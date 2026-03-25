"""Main application entry point."""
"""
Run the Codex Flask application
Default: http://127.0.0.1:5010
Override port with PORT environment variable
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5010))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    host = os.environ.get('HOST', '127.0.0.1')

    print(f"Starting Codex on http://{host}:{port}")
    print(f"Debug mode: {debug}")

    app.run(
        host=host,
        port=port,
        debug=debug
    )

