"""Shared Flask extension instances for YushaCyber.

Extensions are instantiated here, unbound, and initialised against the
application inside the app factory (``app/__init__.py``). This avoids
circular imports and keeps a single instance of each extension that every
module can import safely::

    from extensions import db, login_manager, csrf
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# Database ORM — models across the project bind to this instance.
db = SQLAlchemy()

# Session/user management for login, logout and @login_required.
login_manager = LoginManager()

# Global CSRF protection for every POST form in the application.
csrf = CSRFProtect()
