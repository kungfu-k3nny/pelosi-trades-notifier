import unittest
import os
import sys
import logging
from unittest.mock import patch, MagicMock
import requests
from io import BytesIO

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker import PelosiTradesTracker
from config import load_config
from pdf_parser import download_pdf

# Disable logger output during tests
logging.getLogger("PelosiTracker").setLevel(logging.CRITICAL)

class TestPDFDetection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = load_config()
        self.tracker = PelosiTradesTracker(self.config)
    
    def test_check_for_new_disclosures(self):
        """Test that we can find disclosures on the website"""
        # Use a mock session to prevent actual HTTP requests in tests
        with patch('requests.Session.get') as mock_get, patch('requests.Session.post') as mock_post:
            # Mock the initial page load
            mock_get.return_value.status_code = 200
            
            # Mock the search response with a sample HTML page
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
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = sample_html
            
            disclosures = self.tracker.check_for_new_disclosures()
            
            # Check that we found one disclosure
            self.assertEqual(len(disclosures), 1)
            
            # Check the disclosure has the expected properties
            disclosure = disclosures[0]
            self.assertEqual(disclosure['name'], 'Pelosi, Nancy')
            self.assertEqual(disclosure['office'], 'House of Representatives')
            self.assertEqual(disclosure['filing_year'], '2024')
            self.assertEqual(disclosure['filing_type'], 'Periodic Transaction Report')
            self.assertTrue('pdf_url' in disclosure)
            self.assertTrue(disclosure['pdf_url'].endswith('20012345.pdf'))
    
    def test_download_pdf(self):
        """Test that we can download a PDF file"""
        # Create a mock session
        mock_session = MagicMock()
        
        # Create a mock response with PDF content
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.5\n%Fake PDF content'
        mock_session.get.return_value = mock_response
        
        # Test the download_pdf function
        pdf_url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2023/20012345.pdf"
        pdf_io = download_pdf(mock_session, pdf_url)
        
        # Check that a PDF was downloaded
        self.assertIsInstance(pdf_io, BytesIO)
        pdf_io.seek(0)
        content = pdf_io.read()
        self.assertTrue(content.startswith(b'%PDF'))
        
        # Verify that the session's get method was called with the correct URL
        mock_session.get.assert_called_once_with(pdf_url)

if __name__ == '__main__':
    unittest.main() 