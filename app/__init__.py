"""
Codex - Adobe Analytics Configuration Viewer
Flask application factory
"""
import json
import os
from flask import Flask

from app.services.cache import CacheService
from app.services.git_info import get_git_info


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


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    config = load_config()
    app.config['APP_TITLE'] = config.get('APP_TITLE', 'Codex')
    app.config['AW_REPORTSUITE_ID'] = config.get('AW_REPORTSUITE_ID')
    app.config['REPORTSUITE_NAME'] = config.get('REPORTSUITE_NAME', '')

    # API version selection (default: 2.0)
    app.config['API_VERSION'] = config.get('API_VERSION', '2.0')

    # OAuth2 credentials (API 2.0)
    app.config['CLIENT_ID'] = config.get('CLIENT_ID')
    app.config['CLIENT_SECRET'] = config.get('CLIENT_SECRET')
    app.config['SCOPES'] = config.get('SCOPES')
    app.config['ORGANIZATION_ID'] = config.get('ORGANIZATION_ID')

    # WSSE credentials (API 1.4 - also used for processing rules)
    app.config['AW_USERNAME'] = config.get('AW_USERNAME')
    app.config['AW_SECRET'] = config.get('AW_SECRET')

    # API 1.4 request timeout (seconds); see config.dist.json for guidance
    app.config['API_V14_TIMEOUT'] = config.get('API_V14_TIMEOUT', 5.0)

    # Git info for footer display
    git_info = get_git_info()
    app.config['GIT_BRANCH'] = git_info.get('branch')
    app.config['GIT_COMMIT'] = git_info.get('commit')

    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # Start background cache warmer (warms at startup + every 24h)
    from app.services.cache_warmer import start_scheduler
    app.cache_scheduler = start_scheduler(app)

    return app
