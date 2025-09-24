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
    
    # Quick check without lock - first check if files exist on disk
    if _nltk_setup_done or check_nltk_data():
        _nltk_setup_done = True
        return
    
    with _nltk_setup_lock:
        # Double-check with lock
        if _nltk_setup_done or check_nltk_data():
            _nltk_setup_done = True
            return
        
        try:
            # Set NLTK data path to avoid multiple downloads
            nltk_data_dir = os.path.expanduser("~/nltk_data")
            if nltk_data_dir not in nltk.data.path:
                nltk.data.path.append(nltk_data_dir)
            
            # Create directory if it doesn't exist
            os.makedirs(nltk_data_dir, exist_ok=True)
            
            # Use file-based locking to prevent concurrent downloads across processes
            lock_file = os.path.join(nltk_data_dir, '.nltk_download.lock')
            
            # Check if another process is downloading
            if os.path.exists(lock_file):
                # Wait for other process to finish, then check again
                import time
                max_wait = 60  # Max wait 60 seconds
                waited = 0
                while os.path.exists(lock_file) and waited < max_wait:
                    time.sleep(1)
                    waited += 1
                
                # Check if data is now available
                if check_nltk_data():
                    _nltk_setup_done = True
                    return
            
            # Create lock file to prevent other processes from downloading
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            try:
                # Final check before downloading
                if check_nltk_data():
                    _nltk_setup_done = True
                    return
                
                # Download only if not present
                logger.info("Downloading required NLTK data...")
                
                # Download with quiet mode to reduce output
                nltk.download('wordnet', quiet=True, download_dir=nltk_data_dir)
                nltk.download('punkt', quiet=True, download_dir=nltk_data_dir)
                
                logger.info("NLTK data downloaded successfully")
                _nltk_setup_done = True
                
            finally:
                # Remove lock file
                try:
                    os.remove(lock_file)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error setting up NLTK data: {e}")
            # Don't set _nltk_setup_done to True so it can retry
            raise


def check_nltk_data():
    """Check if NLTK data is available without downloading"""
    try:
        # Ensure NLTK data path is set
        nltk_data_dir = os.path.expanduser("~/nltk_data")
        if nltk_data_dir not in nltk.data.path:
            nltk.data.path.append(nltk_data_dir)
        
        # Try to find the data
        nltk.data.find('corpora/wordnet')
        nltk.data.find('tokenizers/punkt')
        return True
    except LookupError:
        return False
