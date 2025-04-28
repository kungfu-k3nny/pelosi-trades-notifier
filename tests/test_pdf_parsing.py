import unittest
import os
import sys
import json
import logging
import datetime
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
import PyPDF2

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pdf_parser import extract_trades_from_pdf

# Disable logger output during tests
logging.getLogger("DisclosureTracker").setLevel(logging.CRITICAL)

class TestPDFParsing(unittest.TestCase):
    
    def test_extract_trades_from_pdf(self):
        """Test that we can extract trades from a PDF with known content"""
        # Get current year for test data
        current_year = datetime.datetime.now().year
        next_year = current_year + 1
        
        # Create a mock PDF content with known structure
        sample_pdf_text = f"""
        UNITED STATES HOUSE OF REPRESENTATIVES
        Financial Disclosure Report
        
        FILER INFORMATION
        Name: Representative, Test
        Status: Member of Congress
        
        Transactions
        
        ASSET: Alphabet Inc. - Class A (GOOGL)
        Filing Status: New
        Description: Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/{next_year}.
        Date: 01/14/{current_year}
        Notification Date: 01/14/{current_year}
        
        ASSET: Amazon.com, Inc. (AMZN)
        Filing Status: New
        Description: Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/{next_year}.
        Date: 01/14/{current_year}
        Notification Date: 01/14/{current_year}
        
        ASSET: Apple Inc. Common Stock (AAPL)
        Filing Status: New
        Description: Sold 31,600 shares.
        Date: 12/31/{current_year-1 if current_year > 1 else current_year}
        Notification Date: 12/31/{current_year-1 if current_year > 1 else current_year}
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
            self.assertEqual(trades[0]['description'], f'Purchased 50 call options with a strike price of $150 and an expiration date of 1/16/{next_year}.')
            self.assertEqual(trades[0]['transaction_date'], f'01/14/{current_year}')
            self.assertEqual(trades[0]['notification_date'], f'01/14/{current_year}')
            
            # Check the third trade
            self.assertEqual(trades[2]['stock_name'], 'Apple Inc. Common Stock')
            self.assertEqual(trades[2]['ticker'], 'AAPL')
            self.assertEqual(trades[2]['description'], 'Sold 31,600 shares.')
            self.assertEqual(trades[2]['transaction_date'], f'12/31/{current_year-1 if current_year > 1 else current_year}')
            self.assertEqual(trades[2]['notification_date'], f'12/31/{current_year-1 if current_year > 1 else current_year}')
    
    def test_extract_trades_from_empty_pdf(self):
        """Test behavior when processing a PDF with no trade data"""
        # Create a mock PDF with no trades
        sample_pdf_text = """
        UNITED STATES HOUSE OF REPRESENTATIVES
        Financial Disclosure Report
        
        FILER INFORMATION
        Name: Representative, Test
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


def test_real_pdf_parsing(pdf_path):
    """
    Test the PDF parsing functionality on a real financial disclosure PDF.
    
    Args:
        pdf_path: Path to the PDF file to test
    """
    print(f"Testing PDF parsing on: {pdf_path}")
    
    # Read the PDF file
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
            pdf_io = BytesIO(pdf_data)
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return
    
    # Parse the PDF
    try:
        trades = extract_trades_from_pdf(pdf_io)
        
        # Print the results
        print("\nExtracted Trades:")
        print("=" * 80)
        
        for i, trade in enumerate(trades, 1):
            print(f"\nTrade #{i}:")
            
            if "stock_name" in trade and "ticker" in trade:
                # Regular trade information
                print(f"  Stock Name: {trade.get('stock_name', 'N/A')}")
                print(f"  Ticker: {trade.get('ticker', 'N/A')}")
                print(f"  Filing Status: {trade.get('filing_status', 'N/A')}")
                print(f"  Description: {trade.get('description', 'N/A')}")
                print(f"  Transaction Date: {trade.get('transaction_date', 'N/A')}")
                print(f"  Notification Date: {trade.get('notification_date', 'N/A')}")
            elif "note" in trade:
                # Note or error
                print(f"  Note: {trade['note']}")
                if "pdf_text_sample" in trade:
                    print(f"\n  PDF Text Sample (first 200 chars):\n  {trade['pdf_text_sample'][:200]}...")
                if "error" in trade:
                    print(f"  Error: {trade['error']}")
        
        print("\n" + "=" * 80)
        print(f"Total trades found: {len(trades)}")
        
        # Also save the results to a JSON file
        output_file = f"{os.path.splitext(pdf_path)[0]}_parsed.json"
        with open(output_file, "w") as f:
            json.dump(trades, f, indent=2)
        print(f"\nResults saved to: {output_file}")
            
    except Exception as e:
        print(f"Error parsing PDF: {e}")


if __name__ == '__main__':
    # If arguments are provided, run the real PDF test
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        test_real_pdf_parsing(pdf_path)
    else:
        # Otherwise run the unit tests
        unittest.main() 