"""YushaCyber application factory.

Creates and configures the Flask application: loads configuration from the
environment (via python-dotenv), initialises shared extensions, registers
blueprints and keeps the existing homepage route working unchanged.
"""

from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import current_user, login_required

from extensions import csrf, db, login_manager

# Load variables from a project-root .env file, if present.
load_dotenv()


def create_app() -> Flask:
    """Build and return a fully configured YushaCyber application."""
    app = Flask(__name__)

    _configure(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_routes(app)
    _create_tables(app)

    return app


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _configure(app: Flask) -> None:
    """Apply security-conscious configuration from the environment."""
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        # Never hardcode secrets. For development convenience an ephemeral
        # key is generated, which invalidates sessions on every restart.
        # Set SECRET_KEY in .env for a stable key (see .env.example).
        secret_key = secrets.token_hex(32)
        app.logger.warning(
            "SECRET_KEY not set — using an ephemeral development key. "
            "Define SECRET_KEY in your .env file."
        )
    app.config["SECRET_KEY"] = secret_key

    # SQLite for development; the URI can be overridden for production.
    os.makedirs(app.instance_path, exist_ok=True)
    default_db = "sqlite:///" + os.path.join(app.instance_path, "yushacyber.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Session / cookie hardening.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    # Enable secure cookies when served over HTTPS (production).
    secure_cookies = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    app.config["SESSION_COOKIE_SECURE"] = secure_cookies
    app.config["REMEMBER_COOKIE_SECURE"] = secure_cookies


def _init_extensions(app: Flask) -> None:
    """Bind shared extensions to this application instance."""
    db.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access that page."
    login_manager.login_message_category = "error"


def _register_blueprints(app: Flask) -> None:
    """Attach feature blueprints."""
    from app.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")


def _register_routes(app: Flask) -> None:
    """Application-level routes (homepage stays exactly as before)."""

    @app.route("/")
    def index():
        """Render the landing page."""
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """Placeholder for the future dashboard — already login-protected.

        A dedicated dashboard feature will replace this in a later task;
        the route exists now so the @login_required flow can be verified.
        """
        return render_template("auth/dashboard_placeholder.html", user=current_user)


def _create_tables(app: Flask) -> None:
    """Create database tables on first run (development convenience)."""
    with app.app_context():
        # Import models so SQLAlchemy knows about them before create_all().
        from app.auth import models  # noqa: F401

        db.create_all()
