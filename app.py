"""YushaCyber development entry point.

Kept at its original location so the existing run command still works:

    python app/app.py

The application itself now lives in the app factory (``app/__init__.py``).
"""

import os
import sys

# Ensure the project root is importable when this file is run as a script.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app  # noqa: E402  (path setup must run first)

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug)
