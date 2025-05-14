"""Flask extensions module."""
from flask_cors import CORS

# Initialize extensions
cors = CORS()

def init_extensions(app):
    """
    Initialize Flask extensions.
    
    Args:
        app: Flask application instance
    """
    # Initialize CORS
    cors.init_app(app) 