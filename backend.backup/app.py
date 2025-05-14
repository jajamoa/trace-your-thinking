"""Main application factory module."""
import os
from flask import Flask, jsonify
import traceback

# Import order: first config and logging, then other modules
from config import config
from utils.logging import logger

# Then import other modules
from extensions import init_extensions
from api import register_blueprints

# Keep track of app creation to prevent multiple instances
_app_instance = None

def create_app():
    """
    Application factory function.
        
    Returns:
        Flask: Configured Flask application instance
    """
    global _app_instance
    
    # Return existing instance if already created
    if _app_instance is not None:
        logger.info("Returning existing Flask application instance")
        return _app_instance
    
    # Log that we're creating a new app instance
    logger.info("Creating new Flask application instance")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Initialize extensions
    init_extensions(app)
    
    # Register API blueprints
    register_blueprints(app)
    
    # Add global error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Log any uncaught exceptions and return appropriate error response"""
        # Log the stack trace
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return JSON response
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "success": False
        }), 500

    # Log app initialization
    logger.info(f"Initialized application in {config.FLASK_ENV} environment")
    logger.info(f"LLM I/O debug mode is {'ENABLED' if config.DEBUG_LLM_IO else 'DISABLED'}")
    
    # Save instance and return
    _app_instance = app
    return app

# For local development
if __name__ == '__main__':
    app = create_app()
    port = config.PORT
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=config.FLASK_ENV == 'development') 