#!/usr/bin/env python3
"""
Management System
"""

from app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=True,
        use_reloader=False,
        threaded=True,
        host='0.0.0.0',
        port=5001
    )