"""
NLTK Setup Module
Handles NLTK data download in a thread-safe manner
"""
import nltk
import os
import threading
import logging

# Global lock for thread-safe NLTK setup
_nltk_setup_lock = threading.Lock()
_nltk_setup_done = False

logger = logging.getLogger(__name__)


def ensure_nltk_data():
    """
    Ensure NLTK data is downloaded. Thread-safe and process-safe.
    Only downloads if data is not already present.
    """
    global _nltk_setup_done
    
    # Quick check without lock
    if _nltk_setup_done:
        return
    
    with _nltk_setup_lock:
        # Double-check with lock
        if _nltk_setup_done:
            return
        
        try:
            # Check if data already exists
            try:
                nltk.data.find('corpora/wordnet')
                nltk.data.find('tokenizers/punkt')
                logger.debug("NLTK data already present")
                _nltk_setup_done = True
                return
            except LookupError:
                pass
            
            # Set NLTK data path to avoid multiple downloads
            nltk_data_dir = os.path.expanduser("~/nltk_data")
            if nltk_data_dir not in nltk.data.path:
                nltk.data.path.append(nltk_data_dir)
            
            # Download only if not present
            logger.info("Downloading required NLTK data...")
            
            # Download with quiet mode to reduce output
            nltk.download('wordnet', quiet=True)
            nltk.download('punkt', quiet=True)
            
            logger.info("NLTK data downloaded successfully")
            _nltk_setup_done = True
            
        except Exception as e:
            logger.error(f"Error setting up NLTK data: {e}")
            # Don't set _nltk_setup_done to True so it can retry
            raise


def check_nltk_data():
    """Check if NLTK data is available without downloading"""
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('tokenizers/punkt')
        return True
    except LookupError:
        return False
