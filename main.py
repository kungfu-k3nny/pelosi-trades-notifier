import logging
import sys
from tracker import PelosiTradesTracker
from config import load_config

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

def main():
    # Load configuration
    config = load_config()
    
    # Check if configuration is properly set
    email_config = config.get("email", {})
    if (email_config.get("sender_email") == "PLACEHOLDER_EMAIL@gmail.com" or
        email_config.get("sender_password") == "PLACEHOLDER_PASSWORD"):
        logger.error("Please configure your email settings in config.json")
        logger.info("Edit config.json with your email and password before running.")
        return 1
    
    # Initialize and run the tracker
    tracker = PelosiTradesTracker(config)
    try:
        tracker.run_scheduled()
    except KeyboardInterrupt:
        logger.info("Shutting down Pelosi Trades Tracker")
        return 0
    except Exception as e:
        logger.error(f"Error running tracker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 