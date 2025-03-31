import unittest
import os
import sys
import logging
import json
import tempfile
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker import PelosiTradesTracker
from config import load_config

# Disable logger output during tests
logging.getLogger("PelosiTracker").setLevel(logging.CRITICAL)

class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary config with test values
        self.temp_data_file = tempfile.NamedTemporaryFile(delete=False).name
        
        self.config = {
            "base_url": "https://disclosures-clerk.house.gov/FinancialDisclosure",
            "search_url": "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewDisclosurePTP",
            "last_name": "pelosi",
            "filing_year": 2025,
            "check_interval_seconds": 3,
            "data_file": self.temp_data_file,
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "test@example.com",
                "sender_password": "test_password",
                "recipient_email": "recipient@example.com"
            }
        }
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary data file
        if os.path.exists(self.temp_data_file):
            os.remove(self.temp_data_file)
    
    def test_full_disclosure_workflow(self):
        """Test the full workflow of finding, processing, and notifying about disclosures"""
        
        # Sample HTML response for the search
        sample_html = """
        <html>
          <body>
            <table class="table">
              <tr>
                <th>Name</th>
                <th>Office</th>
                <th>Year</th>
                <th>Document</th>
              </tr>
              <tr>
                <td>Pelosi, Nancy</td>
                <td>House of Representatives</td>
                <td>2024</td>
                <td>Periodic Transaction Report <a href="/public_disc/ptr-pdfs/2023/20012345.pdf">View</a></td>
              </tr>
            </table>
          </body>
        </html>
        """
        
        # Sample PDF text
        sample_pdf_text = """
        UNITED STATES HOUSE OF REPRESENTATIVES
        Financial Disclosure Report
        
        FILER INFORMATION
        Name: Pelosi, Nancy
        Status: Member of Congress
        
        Transactions
        
        ASSET: Alphabet Inc. - Class A (GOOGL)
        Filing Status: New
        Description: Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/2026.
        Date: 01/14/2025
        Notification Date: 01/14/2025
        """
        
        # Initialize the tracker with our test config
        tracker = PelosiTradesTracker(self.config)
        
        # Mock requests to return our sample responses
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post, \
             patch('PyPDF2.PdfReader') as mock_pdf_reader, \
             patch('smtplib.SMTP') as mock_smtp:
            
            # Mock HTTP GET to return successful response
            mock_get.return_value.status_code = 200
            
            # Mock HTTP POST to return our sample HTML
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = sample_html
            
            # Mock PDF content
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_pdf_text
            mock_pdf.pages = [mock_page]
            mock_pdf_reader.return_value = mock_pdf
            
            # Mock SMTP for email
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Execute the process
            tracker.process_new_disclosures()
            
            # Verify that the workflow completed successfully
            
            # 1. Check that we made the HTTP requests
            mock_get.assert_called_once()  # For the main page
            mock_post.assert_called_once()  # For the search
            
            # 2. Verify that we extracted PDF content
            mock_pdf_reader.assert_called_once()
            
            # 3. Check that we sent an email notification
            mock_smtp.assert_called_once_with(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            )
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
            
            # 4. Check that we saved the disclosure ID to avoid duplicates
            with open(self.temp_data_file, 'r') as f:
                saved_data = json.load(f)
                self.assertEqual(len(saved_data["processed_disclosures"]), 1)
                self.assertIn("Pelosi, Nancy_Periodic Transaction Report_", saved_data["processed_disclosures"][0])

if __name__ == '__main__':
    unittest.main() 