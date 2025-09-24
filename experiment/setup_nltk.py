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
    
    # Force NLTK setup to ensure it's done before parallel processing
    print("Ensuring NLTK data is available for all worker processes...")
    ensure_nltk_data()
    
    # Verify setup was successful
    if check_nltk_data():
        print("NLTK data setup complete and verified.")
    else:
        print("Warning: NLTK data verification failed.")
        sys.exit(1)
        
except Exception as e:
    print(f"Error setting up NLTK data: {e}")
    sys.exit(1)

print("NLTK setup successful!")

