#!/bin/bash

# Setup script for deploying Pelosi Trades Tracker on GCP VM

# Update package lists
sudo apt update

# Install Python and pip if not already installed
sudo apt install -y python3 python3-pip

# Install Git
sudo apt install -y git

# Create a directory for the application
mkdir -p ~/pelosi-trades-tracker
cd ~/pelosi-trades-tracker

# Copy application files (assuming they're already on the VM)
# If you need to clone from a repository, uncomment the following line:
# git clone https://github.com/yourusername/pelosi-trades-tracker.git .

# Install Python dependencies
pip3 install -r requirements.txt

# Create configuration file from sample if it doesn't exist
if [ ! -f config.json ]; then
    cp config.json.sample config.json
    echo "Created config.json from sample. Please edit this file with your email settings."
    echo "Run: nano config.json"
fi

# Setup a cron job to start the tracker on reboot (optional)
# This will write the current crontab to a file, add our line, and reload it
crontab -l > mycron 2>/dev/null || echo "" > mycron
echo "@reboot cd $PWD && nohup python3 pelosi_trades_tracker.py > tracker.out 2>&1 &" >> mycron
crontab mycron
rm mycron

# Make the tracker script executable
chmod +x pelosi_trades_tracker.py

echo "Setup complete! Now edit 'config.json' to configure your email settings."
echo "To start the tracker immediately, run:"
echo "cd ~/pelosi-trades-tracker && nohup python3 pelosi_trades_tracker.py > tracker.out 2>&1 &" 