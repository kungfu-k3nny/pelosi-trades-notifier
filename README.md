# Financial Disclosure Tracker

This Python application automatically monitors the House financial disclosure website for new filings by all members of Congress, extracts information about stock trades from the disclosure PDFs, and sends email notifications with the details.

## Features

- Automatically checks for new financial disclosures at regular intervals (2 seconds)
- Monitors ALL financial disclosures from the House of Representatives
- Downloads and parses PDF disclosure forms
- Extracts relevant stock trade information including:
  - Stock name and ticker symbol
  - Filing status (New, Amended, etc.)
  - Transaction description
  - Transaction date
  - Notification date
- Sends detailed email notifications to multiple recipients with the disclosure information and PDF attachment
- Tracks previously processed disclosures to avoid duplicate notifications
- Two-tier detection system for faster identification of new disclosures:
  - Quick count-based detection identifies changes in total number of entries
  - Detailed ID-based verification identifies the specific new disclosures
- Always searches for the current filing year automatically (no hardcoded year values)
- Thread-safe execution to prevent resource conflicts
- Infrastructure as Code using Terraform for easy deployment to Google Cloud
- Cost-optimized with budget controls and scaling limits

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

## Project Structure

The project is organized into modular components for better maintainability:

- `main.py` - The entry point that initializes logging and starts the tracker
- `config.py` - Configuration loading and management
- `tracker.py` - Main DisclosureTracker class and core functionality
- `pdf_parser.py` - PDF downloading and parsing functionality
- `notification.py` - Email notification functionality
- `main.tf`, `variables.tf` - Terraform infrastructure configuration
- `setup_terraform.sh` - Helper script for Terraform setup
- `tests/` - Test suite for various components

## Two-Tier Detection System

The application implements an efficient two-tier approach for detecting new disclosures:

1. **Fast Count-Based Detection**:
   - Extracts the total entry count from the results page (e.g., "Showing 1 to 10 of 233 entries")
   - Compares with previously stored count to quickly identify if any new entries exist
   - Provides immediate detection without processing each individual disclosure

2. **Detailed ID-Based Verification**:
   - Once new entries are detected via count, detailed parsing identifies the specific new disclosures
   - Every disclosure is assigned a unique ID based on name, filing type, and PDF URL
   - Only newly identified disclosures are processed, avoiding redundant operations

This approach optimizes performance by:
- Reducing unnecessary processing when no new disclosures exist
- Maintaining a persistent memory of both the expected count and processed disclosure IDs
- Using in-memory caching to minimize disk reads for frequently accessed data

## Tests

The project includes comprehensive tests covering all major components:

1. **PDF Detection Tests** - Verify the ability to find and download PDFs
2. **PDF Parsing Tests** - Ensure proper extraction of trade information from PDFs
3. **Email Notification Tests** - Validate email sending functionality
4. **Integration Tests** - Test the full workflow end-to-end
5. **Count Detection Tests** - Verify accurate extraction of disclosure counts and change detection

### Running Tests

To run all tests:

```bash
python run_tests.py
```

To run a specific test:

```bash
python -m unittest tests.test_pdf_parsing
```

### Live Email Test

There's a special test for sending actual emails that's disabled by default. To run it:

1. Configure your `config.json` with real email credentials
2. Edit `tests/test_email_notification.py` and uncomment the `@unittest.skip` line
3. Run the test with:

```bash
python -m unittest tests.test_email_notification.TestEmailNotification.test_real_email_sending
```

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
- Terraform (optional, for automated deployment)

### Installation

1. Clone this repository to your local machine or GCP VM:

```bash
git clone https://github.com/yourusername/financial-disclosure-tracker.git
cd financial-disclosure-tracker
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
    "recipient_emails": ["recipient1@example.com", "recipient2@example.com"]
}
```

**Note:** For Gmail, you need to generate an "App Password" for this application. Go to your Google Account > Security > 2-Step Verification > App passwords.

4. Adjust the check interval if needed (default is 2 seconds):

```json
"check_interval_seconds": 2
```

### Terraform Deployment (Recommended)

For a streamlined deployment to Google Cloud Platform with cost optimization and autoscaling:

1. Set up your GCP credentials:
```bash
gcloud auth application-default login
```

2. Configure your Terraform variables:
```bash
cp terraform.tfvars.sample terraform.tfvars
nano terraform.tfvars  # Edit with your details
```

3. Run the setup script:
```bash
chmod +x setup_terraform.sh
./setup_terraform.sh
```

4. Apply the Terraform configuration:
```bash
terraform apply
```

The Terraform configuration includes:
- e2-micro instance type (lowest cost VM type)
- Cost optimization with budget alerts at 50%, 80%, and 100% of $50 budget
- Autoscaling limited to maximum 2 instances to control costs
- CPU utilization monitoring and alerts
- Network security configuration

### Running Locally or Manually on GCP VM

1. Create a new VM instance on Google Cloud Platform
2. SSH into your VM
3. Install Git and Python if not already installed
4. Clone the repository and set up as described above
5. Use `nohup` or `screen` to keep the application running after you disconnect:

```bash
# Using nohup
nohup python main.py > tracker.out 2>&1 &

# OR using screen
screen -S disclosure-tracker
python main.py
# Press Ctrl+A, then D to detach the screen
```

## Threading and Performance Considerations

This application uses a single-instance execution pattern to prevent overlapping function calls:

- If a check is still running when the next one is scheduled, the new one will be skipped
- This prevents resource contention and accumulation of tasks
- It's especially important when running with a short interval (2 seconds)

For optimal performance:
- Recommended: e2-small (2 vCPUs, 2GB RAM) or better
- Minimum: e2-micro (2 vCPUs, 1GB RAM) may experience occasional delays during PDF processing

Since 99.999% of operations result in no new disclosures, the e2-micro generally provides sufficient performance while keeping costs low.

## How It Works

1. The application sends a search request to the House financial disclosure website with the current year (dynamically determined)
2. It first checks if the total number of entries has changed since the last check
3. If a change is detected, it parses the HTML response to identify new disclosure links
4. When a new disclosure is found, it downloads the PDF
5. The PDF text is extracted and analyzed to find stock transaction information
6. An email notification is sent to all configured recipients with the disclosure details and PDF attached
7. The disclosure is marked as processed and the expected count is updated to avoid duplicate processing

## Important Note on Volume

This application will track **all** financial disclosures, which could be a substantial number during peak filing periods. Make sure your email system can handle the potential volume of notifications, especially during busy disclosure periods (like quarterly financial disclosure deadlines). You may want to:

- Create a dedicated email folder/label for these notifications
- Consider adjusting the check interval during non-peak periods
- Set up email filters if needed

## Limitations and Possible Improvements

- The PDF parsing is simplified and may need enhancement based on the actual structure of disclosure forms
- Additional error handling and retry logic could be added for improved robustness
- More sophisticated trade detection could be implemented for better accuracy
- The application could be extended to include filtering options (by representative, transaction type, etc.)
- Consider adding pagination support if the number of disclosures exceeds the page size

## License

This project is licensed under the MIT License - see the LICENSE file for details. 