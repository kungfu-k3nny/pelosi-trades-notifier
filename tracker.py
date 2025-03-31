import requests
from bs4 import BeautifulSoup
import json
import os
import logging
import threading
import time
from typing import Dict, List, Optional, Set

from pdf_parser import download_pdf, extract_trades_from_pdf
from notification import send_email_notification

logger = logging.getLogger("PelosiTracker.Tracker")

class PelosiTradesTracker:
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.known_disclosures = self._load_known_disclosures()
        self._is_running = False
        self._lock = threading.Lock()
        
    def _load_known_disclosures(self) -> Set[str]:
        """Load previously processed disclosures from file"""
        if os.path.exists(self.config["data_file"]):
            try:
                with open(self.config["data_file"], "r") as f:
                    data = json.load(f)
                    return set(data.get("processed_disclosures", []))
            except Exception as e:
                logger.error(f"Error loading disclosures file: {e}")
                return set()
        return set()
    
    def _save_known_disclosures(self) -> None:
        """Save processed disclosures to file"""
        try:
            with open(self.config["data_file"], "w") as f:
                json.dump({"processed_disclosures": list(self.known_disclosures)}, f)
        except Exception as e:
            logger.error(f"Error saving disclosures file: {e}")
    
    def check_for_new_disclosures(self) -> List[Dict]:
        """Check for new disclosures and return details of any found"""
        logger.info("Checking for new disclosures...")
        
        try:
            # First, we need to get any CSRF tokens or cookies from the main page
            main_page = self.session.get(self.config["base_url"])
            main_page.raise_for_status()
            
            # Now prepare the search request
            form_data = {
                "LastName": self.config["last_name"],
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
            
            # Parse the search results
            soup = BeautifulSoup(search_response.text, 'html.parser')
            results_table = soup.find('table', class_='table')
            
            if not results_table:
                logger.info("No results table found")
                return []
            
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
            
            return new_disclosures
            
        except Exception as e:
            logger.error(f"Error checking for disclosures: {e}")
            return []
    
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
        new_disclosures = self.check_for_new_disclosures()
        
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
                self._save_known_disclosures()
    
    def run_scheduled(self) -> None:
        """Run the tracker on a schedule"""
        logger.info("Starting Pelosi Trades Tracker")
        
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