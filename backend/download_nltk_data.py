#!/usr/bin/env python3
"""
Download required NLTK data for the application.
Run this script once before starting the application to ensure all necessary data is available.
"""
import nltk
import os
import sys

def download_nltk_data():
    """Download required NLTK data packages."""
    print("Downloading NLTK data packages...")
    
    # Create data directory if it doesn't exist
    nltk_data_dir = os.path.expanduser("~/nltk_data")
    if not os.path.exists(nltk_data_dir):
        os.makedirs(nltk_data_dir)
        print(f"Created NLTK data directory: {nltk_data_dir}")
    
    try:
        # Download WordNet
        nltk.download('wordnet')
        print("Successfully downloaded WordNet")
        
        # Download punkt tokenizer
        nltk.download('punkt')
        print("Successfully downloaded punkt tokenizer")
        
        print("\nAll required NLTK data packages have been downloaded.")
        print(f"Data is stored in: {nltk_data_dir}")
        print("You can now run the application.")
        
        return True
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        return False

if __name__ == "__main__":
    success = download_nltk_data()
    sys.exit(0 if success else 1) 