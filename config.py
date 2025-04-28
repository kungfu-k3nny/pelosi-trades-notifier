import os
import json
import logging
import datetime

logger = logging.getLogger("DisclosureTracker.Config")

def load_config():
    """Load configuration from external file or use defaults"""
    default_config = {
        "base_url": "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "search_url": "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewDisclosurePTP",
        "filing_year": datetime.datetime.now().year,
        "check_interval_seconds": 2,
        "data_file": "financial_disclosures.json",
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "PLACEHOLDER_EMAIL@gmail.com",
            "sender_password": "PLACEHOLDER_PASSWORD",
            "recipient_emails": ["PLACEHOLDER_EMAIL@gmail.com"]
        }
    }
    
    try:
        # Try to load from config.json
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                user_config = json.load(f)
                # Ensure filing_year is always current
                if "filing_year" in user_config and isinstance(user_config["filing_year"], int):
                    user_config["filing_year"] = datetime.datetime.now().year
                return user_config
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