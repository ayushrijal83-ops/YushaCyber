"""YushaCyber application factory.

Creates and configures the Flask application: applies configuration from
``config.py``, initialises shared extensions, registers blueprints and
keeps the existing homepage route working unchanged.
"""

from __future__ import annotations

from flask import Flask, render_template

from app.extensions import csrf, db, login_manager, migrate
from config import INSTANCE_DIR, get_config


def create_app() -> Flask:
    """Build and return a fully configured YushaCyber application."""
    app = Flask(__name__, instance_path=str(INSTANCE_DIR))

    _configure(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_routes(app)
    _register_models()
    _register_cli(app)

    return app


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _configure(app: Flask) -> None:
    """Apply settings from config.py (selected via APP_ENV)."""
    config_class = get_config()
    app.config.from_object(config_class)

    # instance/ must exist before SQLite creates the database file in it.
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    if app.config.get("SECRET_KEY_IS_EPHEMERAL"):
        app.logger.warning(
            "SECRET_KEY not set — using an ephemeral development key. "
            "Define SECRET_KEY in your .env file."
        )


def _init_extensions(app: Flask) -> None:
    """Bind shared extensions to this application instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access that page."
    login_manager.login_message_category = "error"


def _register_blueprints(app: Flask) -> None:
    """Attach feature blueprints."""
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.roadmap import roadmap_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(roadmap_bp, url_prefix="/roadmap")


def _register_routes(app: Flask) -> None:
    """Application-level routes (homepage stays exactly as before)."""

    @app.route("/")
    def index():
        """Render the landing page."""
        return render_template("index.html")


def _register_models() -> None:
    """Import every model module so Alembic sees the full metadata.

    Schema management is migration-only: ``flask db migrate`` diffs this
    metadata against the database and ``flask db upgrade`` applies it.
    db.create_all() is intentionally absent from the project.
    """
    from app.auth import models  # noqa: F401
    from app.roadmap import models as roadmap_models  # noqa: F401


def _register_cli(app: Flask) -> None:
    """Register custom Flask CLI commands."""

    @app.cli.command("seed-roadmap")
    def seed_roadmap_command() -> None:
        """Seed the roadmap curriculum (idempotent — safe to re-run)."""
        from app.roadmap.seed import seed_roadmap

        result = seed_roadmap()
        if result["created"]:
            print("Roadmap seeded successfully.")
        else:
            print("Roadmap already populated — no changes made.")
        print(f"  categories: {result['categories']}")
        print(f"  modules:    {result['modules']}")
        print(f"  lessons:    {result['lessons']}")
