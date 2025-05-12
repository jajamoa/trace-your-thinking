from flask import Blueprint, jsonify
import time
import os

# Use absolute imports instead of relative imports
from config import config
from utils.helpers import get_timestamp

# Create Blueprint
health_bp = Blueprint('health', __name__)

@health_bp.route('/healthz', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring service status.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": get_timestamp()
    })

@health_bp.route('/api/status', methods=['GET'])
def api_status():
    """
    API status endpoint that provides detailed status information for the admin dashboard.
    """
    return jsonify({
        "status": "Running",
        "version": config.API_VERSION,
        "uptime": get_timestamp(),
        "environment": config.FLASK_ENV,
        "timestamp": get_timestamp()
    }) 