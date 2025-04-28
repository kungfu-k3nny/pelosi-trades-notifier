import requests
from bs4 import BeautifulSoup
import json
import os
import logging
import threading
import time
import re
from typing import Dict, List, Optional, Set, Tuple

from pdf_parser import download_pdf, extract_trades_from_pdf
from notification import send_email_notification

logger = logging.getLogger("DisclosureTracker.Tracker")

class DisclosureTracker:
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self._load_data()
        self._is_running = False
        self._lock = threading.Lock()
        # In-memory cache of total disclosures count for current year
        self.current_year = str(self.config["filing_year"])
        self._disclosure_count_cache = self.expected_disclosure_counts.get(self.current_year, 0)
        
    def _load_data(self) -> None:
        """Load previously processed disclosures and count from file"""
        self.known_disclosures = set()
        self.expected_disclosure_counts = {}
        
        if os.path.exists(self.config["data_file"]):
            try:
                with open(self.config["data_file"], "r") as f:
                    data = json.load(f)
                    self.known_disclosures = set(data.get("processed_disclosures", []))
                    
                    # Load counts by year (backward compatibility)
                    if "total_disclosure_count" in data:
                        # Old format - migrate to year-based format
                        current_year = str(self.config["filing_year"])
                        self.expected_disclosure_counts = {
                            current_year: data.get("total_disclosure_count", 0)
                        }
                    else:
                        # New format with counts by year
                        self.expected_disclosure_counts = data.get("total_disclosure_counts_by_year", {})
                    
                    current_year = str(self.config["filing_year"])
                    logger.info(f"Loaded {len(self.known_disclosures)} known disclosures and expecting {self.expected_disclosure_counts.get(current_year, 0)} total disclosures for {current_year}")
            except Exception as e:
                logger.error(f"Error loading disclosures file: {e}")
    
    def _save_data(self) -> None:
        """Save processed disclosures and count to file"""
        try:
            with open(self.config["data_file"], "w") as f:
                json.dump({
                    "processed_disclosures": list(self.known_disclosures),
                    "total_disclosure_counts_by_year": self.expected_disclosure_counts
                }, f)
            # Update the in-memory cache for current year
            current_year = str(self.config["filing_year"])
            self._disclosure_count_cache = self.expected_disclosure_counts.get(current_year, 0)
        except Exception as e:
            logger.error(f"Error saving disclosures file: {e}")
    
    def _extract_total_disclosure_count(self, html_content: str) -> int:
        """Extract the total number of disclosures from the search results page"""
        try:
            # Look for a pattern like "Showing 1 to 10 of 233 entries"
            match = re.search(r'Showing\s+\d+\s+to\s+\d+\s+of\s+(\d+)\s+entries', html_content)
            if match:
                return int(match.group(1))
            
            # Alternative pattern - just look for "of X entries"
            match = re.search(r'of\s+(\d+)\s+entries', html_content)
            if match:
                return int(match.group(1))
            
            # If all else fails, count the rows in the table
            soup = BeautifulSoup(html_content, 'html.parser')
            results_table = soup.find('table', class_='table')
            if results_table:
                rows = results_table.find_all('tr')[1:]  # Skip the header row
                return len(rows)
            
            return 0
        except Exception as e:
            logger.error(f"Error extracting disclosure count: {e}")
            return 0
    
    def check_for_new_disclosures(self) -> Tuple[List[Dict], bool]:
        """
        Check for new disclosures and return details of any found.
        Also returns a flag indicating if a quick check detected new total entries.
        """
        logger.info("Checking for new disclosures...")
        
        try:
            # First, we need to get any CSRF tokens or cookies from the main page
            main_page = self.session.get(self.config["base_url"])
            main_page.raise_for_status()
            
            # Now prepare the search request - only specify the filing year
            form_data = {
                "FilingYear": self.config["filing_year"],
                "State": "",
                "District": ""
            }
            
            # Perform the search
            search_response = self.session.post(
                self.config["search_url"], 
                data=form_data
            )
            search_response.raise_for_status()
            
            # Get the current year as string for dictionary key
            current_year = str(self.config["filing_year"])
            
            # Check total count first for an early indication of new entries
            current_count = self._extract_total_disclosure_count(search_response.text)
            
            # Get the expected count for the current year (or default to 0 if not found)
            expected_count = self.expected_disclosure_counts.get(current_year, 0)
            
            # Determine if there are new entries
            has_new_entries = current_count > expected_count
            
            if has_new_entries:
                logger.info(f"Detected potential new entries for year {current_year}: Previous count: {expected_count}, Current count: {current_count}")
                # Update the expected count in our object and persist it
                self.expected_disclosure_counts[current_year] = current_count
                self._save_data()
            else:
                logger.info(f"No new entries detected for year {current_year} (count still {current_count})")
                
            # Parse the search results to find specific new disclosures
            soup = BeautifulSoup(search_response.text, 'html.parser')
            results_table = soup.find('table', class_='table')
            
            if not results_table:
                logger.info("No results table found")
                return [], has_new_entries
            
            new_disclosures = []
            
            # Process each row in the results table
            rows = results_table.find_all('tr')[1:]  # Skip the header row
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:  # Ensuring we have enough cells
                    name_cell = cells[0]
                    office_cell = cells[1]
                    filing_year_cell = cells[2]
                    filing_cell = cells[3]
                    
                    # Extract disclosure details
                    name = name_cell.text.strip()
                    filing_type = filing_cell.text.strip()
                    
                    # Find the PDF link
                    pdf_link = filing_cell.find('a')
                    if pdf_link and 'href' in pdf_link.attrs:
                        pdf_url = pdf_link['href']
                        if not pdf_url.startswith('http'):
                            pdf_url = f"https://disclosures-clerk.house.gov{pdf_url}"
                        
                        # Generate a unique ID for this disclosure
                        disclosure_id = f"{name}_{filing_type}_{pdf_url}"
                        
                        # Check if this is a new disclosure
                        if disclosure_id not in self.known_disclosures:
                            logger.info(f"Found new disclosure: {disclosure_id}")
                            new_disclosures.append({
                                "name": name,
                                "office": office_cell.text.strip(),
                                "filing_year": filing_year_cell.text.strip(),
                                "filing_type": filing_type,
                                "pdf_url": pdf_url,
                                "disclosure_id": disclosure_id
                            })
            
            return new_disclosures, has_new_entries
            
        except Exception as e:
            logger.error(f"Error checking for disclosures: {e}")
            return [], False
    
    def process_new_disclosures_wrapper(self):
        """Wrapper function that ensures only one instance runs at a time"""
        # Skip if already running
        if self._is_running:
            logging.info("Previous task still running, skipping this execution")
            return
            
        with self._lock:
            self._is_running = True
            
        try:
            self.process_new_disclosures()
        finally:
            with self._lock:
                self._is_running = False
    
    def process_new_disclosures(self) -> None:
        """Check for and process any new disclosures"""
        new_disclosures, has_new_entries = self.check_for_new_disclosures()
        
        # If we detected new entries via count, but no specific new disclosures found
        # (could happen if site updates don't immediately show all new entries)
        if has_new_entries and not new_disclosures:
            logger.info("Detected an increase in total disclosures count but no specific new items found. Will check again later.")
        
        for disclosure in new_disclosures:
            logger.info(f"Processing disclosure: {disclosure['disclosure_id']}")
            
            # Download the PDF
            pdf_io = download_pdf(self.session, disclosure['pdf_url'])
            if not pdf_io:
                logger.error(f"Failed to download PDF for {disclosure['disclosure_id']}")
                continue
            
            # Extract trades from the PDF
            trades = extract_trades_from_pdf(pdf_io)
            
            # Send email notification
            if send_email_notification(self.config, disclosure, trades, pdf_io):
                # Mark this disclosure as processed
                self.known_disclosures.add(disclosure['disclosure_id'])
                self._save_data()
    
    def run_scheduled(self) -> None:
        """Run the tracker on a schedule"""
        logger.info("Starting Financial Disclosure Tracker")
        
        # Import schedule here to avoid circular imports
        import schedule
        
        # Run immediately at startup
        self.process_new_disclosures_wrapper()
        
        # Schedule regular checks
        schedule.every(self.config["check_interval_seconds"]).seconds.do(
            self.process_new_disclosures_wrapper
        )
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(1)  # Check every second if there are pending tasks 