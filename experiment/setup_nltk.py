#!/usr/bin/env python3
"""
Setup NLTK data before running experiments
This ensures all NLTK data is downloaded once before parallel processing
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend modules to trigger NLTK setup
print("Setting up NLTK data...")
try:
    from backend.nltk_setup import ensure_nltk_data, check_nltk_data
    
    # Check if data already exists
    if check_nltk_data():
        print("NLTK data already present.")
    else:
        print("Downloading NLTK data...")
        ensure_nltk_data()
        print("NLTK data setup complete.")
        
except Exception as e:
    print(f"Error setting up NLTK data: {e}")
    sys.exit(1)

print("NLTK setup successful!")
