#!/usr/bin/env python
import sys
import os
import argparse

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_pdf_parsing import test_real_pdf_parsing

def main():
    """Run the PDF parsing test on a real financial disclosure PDF file."""
    parser = argparse.ArgumentParser(description='Test PDF parsing on a real financial disclosure PDF.')
    parser.add_argument('pdf_path', help='Path to the PDF file to test')
    args = parser.parse_args()
    
    # Check if the PDF file exists
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        return 1
    
    # Run the test
    test_real_pdf_parsing(args.pdf_path)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 