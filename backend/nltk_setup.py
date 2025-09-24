"""
NLTK Setup Module
Handles NLTK data download in a thread-safe and process-safe manner
"""
import nltk
import os
import threading
import logging
import time
from pathlib import Path

# Try to import fcntl for Unix systems, fall back for Windows
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

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
    
    # Check if data exists first (fast path)
    if check_nltk_data():
        _nltk_setup_done = True
        return
    
    with _nltk_setup_lock:
        # Double-check with lock
        if _nltk_setup_done:
            return
        
        # Check again after acquiring lock
        if check_nltk_data():
            _nltk_setup_done = True
            return
        
        # Use file-based lock for process synchronization
        nltk_data_dir = os.path.expanduser("~/nltk_data")
        lock_file_path = os.path.join(nltk_data_dir, ".nltk_download.lock")
        
        # Ensure directory exists
        os.makedirs(nltk_data_dir, exist_ok=True)
        
        try:
            # Try to acquire process lock (platform-specific)
            lock_acquired = False
            
            if HAS_FCNTL:
                # Unix/Linux: Use fcntl for file locking
                try:
                    with open(lock_file_path, 'w') as lock_file:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_acquired = True
                        
                        # Perform download under lock
                        _download_nltk_data(nltk_data_dir)
                        
                except (IOError, OSError):
                    # Lock is held by another process
                    lock_acquired = False
            else:
                # Windows/other: Use file existence as simple lock
                try:
                    # Try to create lock file exclusively
                    lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(lock_fd)
                    lock_acquired = True
                    
                    try:
                        # Perform download under lock
                        _download_nltk_data(nltk_data_dir)
                    finally:
                        # Clean up lock file
                        try:
                            os.unlink(lock_file_path)
                        except:
                            pass
                            
                except (IOError, OSError):
                    # Lock file already exists
                    lock_acquired = False
            
            if not lock_acquired:
                # Another process is downloading, wait and check
                logger.debug("Another process is downloading NLTK data, waiting...")
                
                # Wait up to 60 seconds for download to complete
                for wait_time in range(60):
                    time.sleep(1)
                    if check_nltk_data():
                        logger.debug("NLTK data downloaded by another process")
                        _nltk_setup_done = True
                        return
                
                # If still not available after waiting, try downloading anyway
                logger.warning("Timeout waiting for other process, attempting download...")
                if not check_nltk_data():
                    _download_nltk_data(nltk_data_dir)
                    
        except Exception as e:
            logger.error(f"Error setting up NLTK data: {e}")
            # Don't set _nltk_setup_done to True so it can retry
            raise
        finally:
            # Clean up lock file if we created it (fcntl version only)
            if HAS_FCNTL:
                try:
                    if os.path.exists(lock_file_path):
                        os.unlink(lock_file_path)
                except:
                    pass


def _download_nltk_data(nltk_data_dir):
    """Internal function to download NLTK data"""
    global _nltk_setup_done
    
    # Check one more time if another process downloaded while we waited
    if check_nltk_data():
        logger.debug("NLTK data already present, skipping download")
        _nltk_setup_done = True
        return
    
    # Set NLTK data path
    if nltk_data_dir not in nltk.data.path:
        nltk.data.path.append(nltk_data_dir)
    
    # Download NLTK data
    logger.info("Downloading required NLTK data...")
    
    try:
        nltk.download('wordnet', quiet=True, download_dir=nltk_data_dir)
        nltk.download('punkt', quiet=True, download_dir=nltk_data_dir)
        
        # Verify download
        if check_nltk_data():
            logger.info("NLTK data downloaded successfully")
            _nltk_setup_done = True
        else:
            raise Exception("NLTK data download verification failed")
            
    except Exception as download_error:
        logger.error(f"Error downloading NLTK data: {download_error}")
        raise


def check_nltk_data():
    """Check if NLTK data is available without downloading"""
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('tokenizers/punkt')
        return True
    except LookupError:
        return False
