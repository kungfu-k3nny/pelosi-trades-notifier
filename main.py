import logging
import sys
from tracker import DisclosureTracker
from config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disclosure_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DisclosureTracker")

def main():
    # Load configuration
    config = load_config()
    
    # Check if configuration is properly set
    email_config = config.get("email", {})
    if (email_config.get("sender_email") == "PLACEHOLDER_EMAIL@gmail.com" or
        email_config.get("sender_password") == "PLACEHOLDER_PASSWORD" or
        not email_config.get("recipient_emails") or
        (len(email_config.get("recipient_emails", [])) == 1 and 
         email_config.get("recipient_emails")[0] == "PLACEHOLDER_EMAIL@gmail.com")):
        logger.error("Please configure your email settings in config.json")
        logger.info("Edit config.json with your email, password, and recipient emails before running.")
        return 1
    
    # Initialize and run the tracker
    tracker = DisclosureTracker(config)
    try:
        tracker.run_scheduled()
    except KeyboardInterrupt:
        logger.info("Shutting down Financial Disclosure Tracker")
        return 0
    except Exception as e:
        logger.error(f"Error running tracker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 