#!/usr/bin/env python
"""
Development server runner script.
Run this script from the backend directory to start the development server.
"""
import os
import sys
import importlib

# Clear any cached modules to prevent conflicts
for module in list(sys.modules.keys()):
    if module.startswith('app') or module.startswith('config') or \
       module.startswith('models') or module.startswith('services') or \
       module.startswith('api') or module.startswith('utils'):
        sys.modules.pop(module, None)

# Set up Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Prioritize current directory in Python path
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import application components
from app import create_app
from config import config
from utils.logging import logger

if __name__ == "__main__":
    # Create application
    app = create_app()
    
    # Run development server
    port = config.PORT
    logger.info(f"Starting development server on port {port}")
    logger.info(f"Running in {config.FLASK_ENV} mode")
    
    # Use debug mode but disable auto-reloader to prevent duplicate logs
    use_debug = config.FLASK_ENV == 'development'
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=use_debug,
        use_reloader=False  # Disable auto-reloader to prevent duplicate initialization
    ) 