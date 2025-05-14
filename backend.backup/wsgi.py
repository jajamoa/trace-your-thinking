"""WSGI entry point for production deployment."""
import os
import sys

# Set up proper Python path for package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)  # Add parent directory to Python path

# 先导入日志工具
from utils.logging import logger

# 再导入应用
from app import create_app

# Create application instance
application = create_app()

if __name__ == "__main__":
    # Import config when run directly
    from config import config
    
    # Run the application
    port = config.PORT
    logger.info(f"Starting server on port {port}")
    application.run(host='0.0.0.0', port=port) 