import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO
from typing import Dict, List, Optional

logger = logging.getLogger("PelosiTracker.Notification")

def send_email_notification(config: Dict, disclosure: Dict, trades: List[Dict], pdf_io: Optional[BytesIO] = None) -> bool:
    """Send an email notification about a new disclosure"""
    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = config["email"]["sender_email"]
        msg['To'] = config["email"]["recipient_email"]
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
        with smtplib.SMTP(config["email"]["smtp_server"], config["email"]["smtp_port"]) as server:
            server.starttls()
            server.login(config["email"]["sender_email"], config["email"]["sender_password"])
            server.send_message(msg)
        
        logger.info(f"Email notification sent for disclosure: {disclosure['disclosure_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        return False 