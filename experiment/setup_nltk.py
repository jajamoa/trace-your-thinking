#!/usr/bin/env python3
"""
Setup NLTK data before running experiments
This ensures all NLTK data is downloaded once before parallel processing
"""
import sys
import os
import nltk

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend modules to trigger NLTK setup
print("Checking NLTK data...")
try:
    from backend.nltk_setup import ensure_nltk_data, check_nltk_data
    
    # Show NLTK data path
    nltk_data_path = os.path.expanduser("~/nltk_data")
    print(f"NLTK data path: {nltk_data_path}")
    
    # Check if data already exists
    if check_nltk_data():
        print("✓ NLTK data already present. No download needed.")
        # Show what's available
        try:
            wordnet_path = nltk.data.find('corpora/wordnet')
            punkt_path = nltk.data.find('tokenizers/punkt')
            print(f"  - WordNet: {wordnet_path}")
            print(f"  - Punkt: {punkt_path}")
        except:
            pass
    else:
        print("NLTK data not found. Downloading...")
        ensure_nltk_data()
        print("✓ NLTK data downloaded successfully.")
        
except Exception as e:
    print(f"✗ Error setting up NLTK data: {e}")
    sys.exit(1)

print("\n✓ NLTK setup complete. Workers will reuse existing data.")

