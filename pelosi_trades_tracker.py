import requests
from bs4 import BeautifulSoup
import re
import os
import time
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import PyPDF2
from io import BytesIO
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Set
import schedule
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pelosi_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PelosiTracker")

# Load configuration from external file
def load_config():
    """Load configuration from external file or use defaults"""
    default_config = {
        "base_url": "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "search_url": "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewDisclosurePTP",
        "last_name": "pelosi",
        "filing_year": datetime.datetime.now().year,
        "check_interval_seconds": 3,
        "data_file": "pelosi_disclosures.json",
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "PLACEHOLDER_EMAIL@gmail.com",
            "sender_password": "PLACEHOLDER_PASSWORD",
            "recipient_email": "PLACEHOLDER_EMAIL@gmail.com"
        }
    }
    
    try:
        # Try to load from config.json
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                return json.load(f)
        else:
            logger.warning("config.json not found. Using default configuration.")
            # Create a sample config file if it doesn't exist
            with open("config.json.sample", "w") as f:
                json.dump(default_config, f, indent=4)
            logger.info("Created config.json.sample. Please edit this file and rename to config.json.")
            return default_config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return default_config

# Load the configuration
CONFIG = load_config()


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
    
    def download_pdf(self, pdf_url: str) -> Optional[BytesIO]:
        """Download a PDF from the given URL"""
        try:
            response = self.session.get(pdf_url)
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            logger.error(f"Error downloading PDF from {pdf_url}: {e}")
            return None
    
    def extract_trades_from_pdf(self, pdf_io: BytesIO) -> List[Dict]:
        """
        Extract trade information from a PDF.
        Extracts stock name, ticker symbol, filing status, description, transaction date, 
        and notification date for each transaction in the disclosure.
        """
        trades = []
        try:
            reader = PyPDF2.PdfReader(pdf_io)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # Skip title and filer information sections
            # Look for the "Transactions" section which contains the trade details
            if "Transactions" in text:
                transactions_section = text.split("Transactions", 1)[1]
            else:
                transactions_section = text
            
            # Regular expressions to match transaction patterns
            # This pattern looks for stock/asset information with ticker symbols in parentheses
            asset_pattern = r'(?:Common Stock|Stock)(?:\s*\(([A-Z]+)\))?'
            
            # Filing status pattern
            filing_status_pattern = r'Filing Status:\s*([^\n]+)'
            
            # Description pattern - captures content after "Description:" until the next section
            description_pattern = r'Description:\s*([^\n]+)'
            
            # Date patterns
            date_pattern = r'(\d{2}/\d{2}/\d{4})'
            
            # Find individual transaction blocks
            # This is a simplified approach - actual implementation would need to be adapted 
            # based on the exact structure of the PDF
            
            # Look for asset mentions which typically indicate a transaction
            asset_matches = re.finditer(asset_pattern, transactions_section)
            
            for match in asset_matches:
                # Extract relevant text around this asset mention
                start_pos = max(0, match.start() - 200)  # Look back 200 chars for context
                end_pos = min(len(transactions_section), match.end() + 500)  # Look ahead 500 chars
                transaction_block = transactions_section[start_pos:end_pos]
                
                # Extract stock name - look for lines ending with the ticker in parentheses
                stock_match = re.search(r'([A-Za-z0-9\s.,&]+)(?:\(([A-Z]+)\))', transaction_block)
                if stock_match:
                    stock_name = stock_match.group(1).strip()
                    ticker = stock_match.group(2).strip()
                else:
                    # Fallback if pattern doesn't match
                    stock_name = "Unknown"
                    ticker = "Unknown"
                
                # Extract filing status
                filing_status_match = re.search(filing_status_pattern, transaction_block)
                filing_status = filing_status_match.group(1).strip() if filing_status_match else "Unknown"
                
                # Extract description
                description_match = re.search(description_pattern, transaction_block)
                description = description_match.group(1).strip() if description_match else "Unknown"
                
                # Extract dates
                date_matches = list(re.finditer(date_pattern, transaction_block))
                transaction_date = date_matches[0].group(1) if len(date_matches) >= 1 else "Unknown"
                notification_date = date_matches[1].group(1) if len(date_matches) >= 2 else "Unknown"
                
                trade = {
                    "stock_name": stock_name,
                    "ticker": ticker,
                    "filing_status": filing_status,
                    "description": description,
                    "transaction_date": transaction_date,
                    "notification_date": notification_date
                }
                
                trades.append(trade)
            
            # If no trades found with the pattern approach, return a note
            if not trades:
                trades.append({
                    "note": "Automatic parsing could not identify specific trades.",
                    "pdf_text_sample": text[:500] + "..." if len(text) > 500 else text
                })
                
            return trades
            
        except Exception as e:
            logger.error(f"Error extracting trades from PDF: {e}")
            return [{
                "error": str(e),
                "note": "Failed to parse PDF. Manual review required."
            }]
    
    def send_email_notification(self, disclosure: Dict, trades: List[Dict], pdf_io: Optional[BytesIO] = None) -> bool:
        """Send an email notification about a new disclosure"""
        try:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["sender_email"]
            msg['To'] = self.config["email"]["recipient_email"]
            msg['Subject'] = f"New Financial Disclosure from {disclosure['name']}"
            
            # Create email body
            body = f"""
            <html>
            <body>
                <h2>New Financial Disclosure Detected</h2>
                <p><strong>Name:</strong> {disclosure['name']}</p>
                <p><strong>Filing Type:</strong> {disclosure['filing_type']}</p>
                <p><strong>Filing Year:</strong> {disclosure['filing_year']}</p>
                <p><strong>Office:</strong> {disclosure['office']}</p>
                <p><strong>PDF URL:</strong> <a href="{disclosure['pdf_url']}">{disclosure['pdf_url']}</a></p>
                
                <h3>Detected Trades:</h3>
                <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #f2f2f2;">
                        <th>Stock Name</th>
                        <th>Ticker</th>
                        <th>Filing Status</th>
                        <th>Description</th>
                        <th>Transaction Date</th>
                        <th>Notification Date</th>
                    </tr>
            """
            
            for trade in trades:
                if "stock_name" in trade and "ticker" in trade:
                    body += f"""
                    <tr>
                        <td>{trade.get('stock_name', 'N/A')}</td>
                        <td>{trade.get('ticker', 'N/A')}</td>
                        <td>{trade.get('filing_status', 'N/A')}</td>
                        <td>{trade.get('description', 'N/A')}</td>
                        <td>{trade.get('transaction_date', 'N/A')}</td>
                        <td>{trade.get('notification_date', 'N/A')}</td>
                    </tr>
                    """
                elif "note" in trade:
                    body += f"""
                    <tr>
                        <td colspan="6"><em>{trade['note']}</em></td>
                    </tr>
                    """
                    if "pdf_text_sample" in trade:
                        body += f"""
                        <tr>
                            <td colspan="6" style="font-family: monospace; font-size: 0.8em;">
                                {trade['pdf_text_sample']}
                            </td>
                        </tr>
                        """
            
            body += """
                </table>
                <p>This is an automated notification.</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Attach the PDF if available
            if pdf_io:
                pdf_io.seek(0)
                pdf_attachment = MIMEApplication(pdf_io.read(), _subtype="pdf")
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{disclosure['name']}_{disclosure['filing_type']}.pdf")
                msg.attach(pdf_attachment)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.config["email"]["smtp_server"], self.config["email"]["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["email"]["sender_email"], self.config["email"]["sender_password"])
                server.send_message(msg)
            
            logger.info(f"Email notification sent for disclosure: {disclosure['disclosure_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
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
            pdf_io = self.download_pdf(disclosure['pdf_url'])
            if not pdf_io:
                logger.error(f"Failed to download PDF for {disclosure['disclosure_id']}")
                continue
            
            # Extract trades from the PDF
            trades = self.extract_trades_from_pdf(pdf_io)
            
            # Send email notification
            if self.send_email_notification(disclosure, trades, pdf_io):
                # Mark this disclosure as processed
                self.known_disclosures.add(disclosure['disclosure_id'])
                self._save_known_disclosures()
    
    def run_scheduled(self) -> None:
        """Run the tracker on a schedule"""
        logger.info("Starting Pelosi Trades Tracker")
        
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


if __name__ == "__main__":
    # Check if configuration is properly set
    email_config = CONFIG.get("email", {})
    if (email_config.get("sender_email") == "PLACEHOLDER_EMAIL@gmail.com" or
        email_config.get("sender_password") == "PLACEHOLDER_PASSWORD"):
        logger.error("Please configure your email settings in config.json")
        logger.info("Edit config.json with your email and password before running.")
        exit(1)
        
    tracker = PelosiTradesTracker(CONFIG)
    tracker.run_scheduled() 