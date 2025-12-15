"""
Codex - Adobe Analytics Configuration Viewer
Flask application factory
"""
import json
import os
from flask import Flask

from app.services.cache import CacheService

# Default port for local development
DEFAULT_DEV_PORT = 5010


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"config.json not found at {config_path}. "
            "Copy config.dist.json to config.json and fill in your credentials."
        )

    with open(config_path, 'r') as f:
        return json.load(f)


def is_development_environment() -> bool:
    """
    Determine if the application is running in development environment.
    
    Returns True if either:
    - FLASK_DEBUG environment variable is set to 'true'
    - PORT environment variable is explicitly set to the dev port (5010)
    """
    # Check FLASK_DEBUG flag
    if os.environ.get('FLASK_DEBUG', 'false').lower() == 'true':
        return True
    
    # Check if PORT is explicitly set to development port
    port_str = os.environ.get('PORT')
    if port_str is not None:
        try:
            port = int(port_str)
            if port == DEFAULT_DEV_PORT:
                return True
        except ValueError:
            # Invalid PORT value, ignore
            pass
    
    return False


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    config = load_config()
    app_title = config.get('APP_TITLE', 'Codex')
    
    # Use 'Dev' title in development environment
    if is_development_environment():
        app_title = 'Dev'
    
    app.config['APP_TITLE'] = app_title
    app.config['AW_REPORTSUITE_ID'] = config.get('AW_REPORTSUITE_ID')
    app.config['AW_USERNAME'] = config.get('AW_USERNAME')
    app.config['AW_SECRET'] = config.get('AW_SECRET')

    # Clear cached API responses so each restart fetches fresh data
    try:
        CacheService().clear_all()
        app.logger.info("Cleared cache directory on startup")
    except Exception as exc:
        app.logger.warning("Failed to clear cache on startup: %s", exc)

    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
