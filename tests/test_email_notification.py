import unittest
import os
import sys
import logging
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from notification import send_email_notification

# Disable logger output during tests
logging.getLogger("PelosiTracker").setLevel(logging.CRITICAL)

class TestEmailNotification(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "test@example.com",
                "sender_password": "test_password",
                "recipient_email": "recipient@example.com"
            }
        }
        
        self.disclosure = {
            "name": "Pelosi, Nancy",
            "office": "House of Representatives",
            "filing_year": "2024",
            "filing_type": "Periodic Transaction Report",
            "pdf_url": "https://example.com/file.pdf",
            "disclosure_id": "unique_id_123"
        }
        
        self.trades = [
            {
                "stock_name": "Alphabet Inc. - Class A",
                "ticker": "GOOGL",
                "filing_status": "New",
                "description": "Purchased 50 call options",
                "transaction_date": "01/14/2025",
                "notification_date": "01/14/2025"
            },
            {
                "stock_name": "Apple Inc.",
                "ticker": "AAPL",
                "filing_status": "New",
                "description": "Sold 31,600 shares",
                "transaction_date": "12/31/2024",
                "notification_date": "12/31/2024"
            }
        ]
        
        # A sample PDF content
        self.pdf_io = BytesIO(b'%PDF-1.5\nSample PDF content')
    
    def test_send_email_notification(self):
        """Test that we can send an email notification"""
        # Mock the SMTP class
        with patch('smtplib.SMTP') as mock_smtp:
            # Set up the mock instance
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Call the function
            result = send_email_notification(
                self.config, 
                self.disclosure, 
                self.trades, 
                self.pdf_io
            )
            
            # Check that the email was sent successfully
            self.assertTrue(result)
            
            # Verify SMTP calls
            mock_smtp.assert_called_once_with(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            )
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with(
                self.config["email"]["sender_email"],
                self.config["email"]["sender_password"]
            )
            mock_server.send_message.assert_called_once()
    
    def test_send_email_notification_without_pdf(self):
        """Test sending an email notification without a PDF attachment"""
        # Mock the SMTP class
        with patch('smtplib.SMTP') as mock_smtp:
            # Set up the mock instance
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Call the function without a PDF
            result = send_email_notification(
                self.config, 
                self.disclosure, 
                self.trades, 
                None  # No PDF
            )
            
            # Check that the email was sent successfully
            self.assertTrue(result)
            
            # Verify SMTP calls
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
    
    def test_send_email_notification_error(self):
        """Test error handling when SMTP fails"""
        # Mock the SMTP class to raise an exception
        with patch('smtplib.SMTP', side_effect=Exception("SMTP error")):
            # Call the function
            result = send_email_notification(
                self.config, 
                self.disclosure, 
                self.trades, 
                self.pdf_io
            )
            
            # Check that the function returned False due to error
            self.assertFalse(result)

    @unittest.skip("This test sends a real email - only run manually after configuring real credentials")
    def test_real_email_sending(self):
        """
        Test sending an actual email (skipped by default).
        
        To run this test:
        1. Set up your config.json with real email credentials
        2. Comment out the @unittest.skip decorator
        3. Run this test specifically with:
           python -m unittest tests.test_email_notification.TestEmailNotification.test_real_email_sending
        """
        import json
        
        # Load real configuration from config.json
        try:
            with open("config.json", "r") as f:
                real_config = json.load(f)
                
            # Send a real email
            result = send_email_notification(
                real_config, 
                self.disclosure, 
                self.trades, 
                self.pdf_io
            )
            
            # Check that the email was sent successfully
            self.assertTrue(result)
            
        except FileNotFoundError:
            self.skipTest("config.json not found - cannot run real email test")
        except json.JSONDecodeError:
            self.skipTest("Invalid JSON in config.json - cannot run real email test")

if __name__ == '__main__':
    unittest.main() 