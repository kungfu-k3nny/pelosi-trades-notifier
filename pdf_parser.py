import PyPDF2
import re
import logging
import requests
from io import BytesIO
from typing import Dict, List, Optional

logger = logging.getLogger("PelosiTracker.PDFParser")

def download_pdf(session, pdf_url: str) -> Optional[BytesIO]:
    """Download a PDF from the given URL"""
    try:
        response = session.get(pdf_url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Error downloading PDF from {pdf_url}: {e}")
        return None

def extract_trades_from_pdf(pdf_io: BytesIO) -> List[Dict]:
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