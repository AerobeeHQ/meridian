#!/usr/bin/env python3
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

    print(f"Starting Codex on http://127.0.0.1:{port}")
    print(f"Debug mode: {debug}")

    app.run(
        host='127.0.0.1',
        port=port,
        debug=debug
    )

