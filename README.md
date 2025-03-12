# Pelosi Trades Tracker

This Python application automatically monitors the House financial disclosure website for new filings by Nancy Pelosi, extracts information about stock trades from the disclosure PDFs, and sends email notifications with the details.

## Features

- Automatically checks for new financial disclosures at regular intervals (3 seconds)
- Downloads and parses PDF disclosure forms
- Extracts relevant stock trade information including:
  - Stock name and ticker symbol
  - Filing status (New, Amended, etc.)
  - Transaction description
  - Transaction date
  - Notification date
- Sends detailed email notifications with the disclosure information and PDF attachment
- Tracks previously processed disclosures to avoid duplicate notifications
- Thread-safe execution to prevent resource conflicts

## PDF Parsing Methodology

The application uses a pattern-matching approach to extract financial trade information from disclosure PDFs. Below is a comparison of the two methods that were considered:

### Method 1: Custom Regex Pattern Matching (Implemented)

**Pros:**
- No external API dependencies or costs
- Complete control over parsing logic
- No privacy concerns as all processing happens locally
- No rate limits or quota constraints
- Works offline without internet connectivity

**Cons:**
- Less adaptable to changes in PDF format
- May require maintenance if disclosure formats change
- Less sophisticated than AI-powered solutions for complex documents
- May not handle all edge cases perfectly

### Method 2: AI-Powered PDF Parsing

**Pros:**
- Potentially more accurate for complex document structures
- Better adaptability to format changes
- Less maintenance required for parsing logic
- Could handle a wider variety of edge cases

**Cons:**
- Requires external API dependencies (potentially paid services)
- Privacy concerns for sensitive financial data
- Rate limits or quotas may apply
- Internet connectivity required
- May have higher latency due to API calls

We implemented Method 1 as it provides a good balance of functionality, privacy, and independence from external services, while being sufficient for the task of parsing standard disclosure PDFs.

## Security and Configuration

This application uses a separate configuration file to store sensitive information:

1. Copy `config.json.sample` to `config.json`
2. Edit `config.json` with your actual email credentials and settings
3. `config.json` is included in `.gitignore` to prevent accidentally exposing your credentials

**Never commit your actual credentials to Git.**

## Setup

### Prerequisites

- Python 3.7+
- A Google account for sending email notifications
- A Google Cloud Platform (GCP) account for hosting the service

### Installation

1. Clone this repository to your local machine or GCP VM:

```bash
git clone https://github.com/yourusername/pelosi-trades-tracker.git
cd pelosi-trades-tracker
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your settings:

```bash
cp config.json.sample config.json
nano config.json  # Or use your preferred editor
```

Update at minimum these values:
```json
"email": {
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipient_email": "where-to-send@example.com"
}
```

**Note:** For Gmail, you need to generate an "App Password" for this application. Go to your Google Account > Security > 2-Step Verification > App passwords.

4. Adjust the check interval if needed:

```json
"check_interval_seconds": 3
```

### Running on GCP VM

1. Create a new VM instance on Google Cloud Platform
2. SSH into your VM
3. Install Git and Python if not already installed
4. Clone the repository and set up as described above
5. Use `nohup` or `screen` to keep the application running after you disconnect:

```bash
# Using nohup
nohup python pelosi_trades_tracker.py > tracker.out 2>&1 &

# OR using screen
screen -S pelosi-tracker
python pelosi_trades_tracker.py
# Press Ctrl+A, then D to detach the screen
```

## Threading and Performance Considerations

This application uses a single-instance execution pattern to prevent overlapping function calls:

- If a check is still running when the next one is scheduled, the new one will be skipped
- This prevents resource contention and accumulation of tasks
- It's especially important when running with a short interval (3 seconds)

For optimal performance:
- Recommended: e2-small (2 vCPUs, 2GB RAM) or better
- Minimum: e2-micro (2 vCPUs, 1GB RAM) may experience occasional delays during PDF processing

Since 99.999% of operations result in no new disclosures, the e2-small provides a good balance between cost and performance.

## How It Works

1. The application sends a search request to the House financial disclosure website with Pelosi's last name and the current year
2. It parses the HTML response to find disclosure links
3. When a new disclosure is found, it downloads the PDF
4. The PDF text is extracted and analyzed to find stock transaction information
5. An email notification is sent with the disclosure details and the PDF attached
6. The disclosure is marked as processed to avoid duplicate notifications

## Limitations and Possible Improvements

- The PDF parsing is simplified and may need enhancement based on the actual structure of disclosure forms
- Additional error handling and retry logic could be added for improved robustness
- More sophisticated trade detection could be implemented for better accuracy
- The application could be extended to track multiple representatives

## License

This project is licensed under the MIT License - see the LICENSE file for details. 