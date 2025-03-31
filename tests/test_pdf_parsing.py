import unittest
import os
import sys
import logging
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
import PyPDF2

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pdf_parser import extract_trades_from_pdf

# Disable logger output during tests
logging.getLogger("PelosiTracker").setLevel(logging.CRITICAL)

class TestPDFParsing(unittest.TestCase):
    
    def test_extract_trades_from_pdf(self):
        """Test that we can extract trades from a PDF with known content"""
        # Create a mock PDF content with known structure
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
        
        ASSET: Amazon.com, Inc. (AMZN)
        Filing Status: New
        Description: Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/2026.
        Date: 01/14/2025
        Notification Date: 01/14/2025
        
        ASSET: Apple Inc. Common Stock (AAPL)
        Filing Status: New
        Description: Sold 31,600 shares.
        Date: 12/31/2024
        Notification Date: 12/31/2024
        """
        
        # Create a mock PDF reader
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = sample_pdf_text
        mock_pdf.pages = [mock_page]
        
        # Mock the PdfReader constructor to return our mock PDF
        with patch('PyPDF2.PdfReader', return_value=mock_pdf):
            # Create a BytesIO object with dummy content
            pdf_io = BytesIO(b'dummy content')
            
            # Extract trades from the mock PDF
            trades = extract_trades_from_pdf(pdf_io)
            
            # Check that we extracted the expected trades
            self.assertEqual(len(trades), 3)
            
            # Check the first trade
            self.assertEqual(trades[0]['stock_name'], 'Alphabet Inc. - Class A')
            self.assertEqual(trades[0]['ticker'], 'GOOGL')
            self.assertEqual(trades[0]['filing_status'], 'New')
            self.assertEqual(trades[0]['description'], 'Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/2026.')
            self.assertEqual(trades[0]['transaction_date'], '01/14/2025')
            self.assertEqual(trades[0]['notification_date'], '01/14/2025')
            
            # Check the third trade
            self.assertEqual(trades[2]['stock_name'], 'Apple Inc. Common Stock')
            self.assertEqual(trades[2]['ticker'], 'AAPL')
            self.assertEqual(trades[2]['description'], 'Sold 31,600 shares.')
            self.assertEqual(trades[2]['transaction_date'], '12/31/2024')
            self.assertEqual(trades[2]['notification_date'], '12/31/2024')
    
    def test_extract_trades_from_empty_pdf(self):
        """Test behavior when processing a PDF with no trade data"""
        # Create a mock PDF with no trades
        sample_pdf_text = """
        UNITED STATES HOUSE OF REPRESENTATIVES
        Financial Disclosure Report
        
        FILER INFORMATION
        Name: Pelosi, Nancy
        Status: Member of Congress
        
        No transactions to report.
        """
        
        # Create a mock PDF reader
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = sample_pdf_text
        mock_pdf.pages = [mock_page]
        
        # Mock the PdfReader constructor to return our mock PDF
        with patch('PyPDF2.PdfReader', return_value=mock_pdf):
            # Create a BytesIO object with dummy content
            pdf_io = BytesIO(b'dummy content')
            
            # Extract trades from the mock PDF
            trades = extract_trades_from_pdf(pdf_io)
            
            # Check that we got a note about no trades found
            self.assertEqual(len(trades), 1)
            self.assertIn('note', trades[0])
            self.assertIn('pdf_text_sample', trades[0])
    
    def test_extract_trades_error_handling(self):
        """Test error handling when PDF processing fails"""
        # Mock PdfReader to raise an exception
        with patch('PyPDF2.PdfReader', side_effect=Exception("PDF parsing error")):
            # Create a BytesIO object with dummy content
            pdf_io = BytesIO(b'dummy content')
            
            # Extract trades from the mock PDF
            trades = extract_trades_from_pdf(pdf_io)
            
            # Check that we got an error message
            self.assertEqual(len(trades), 1)
            self.assertIn('error', trades[0])
            self.assertIn('note', trades[0])
            self.assertEqual(trades[0]['error'], 'PDF parsing error')

if __name__ == '__main__':
    unittest.main() 