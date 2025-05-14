"""API endpoints for the application."""
from flask import Flask

# Use absolute imports instead of relative imports
from api.health import health_bp
from api.cbn import cbn_bp

def register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(health_bp)
    app.register_blueprint(cbn_bp) 