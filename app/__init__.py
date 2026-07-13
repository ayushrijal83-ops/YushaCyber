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
    from app.ctf import ctf_bp
    from app.admin import admin_bp
    from app.labs import labs_bp
    from app.resources import resources_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(roadmap_bp, url_prefix="/roadmap")
    app.register_blueprint(ctf_bp, url_prefix="/ctf")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(labs_bp, url_prefix="/labs")
    app.register_blueprint(resources_bp, url_prefix="/resources")


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
    from app.achievement import models as achievement_models  # noqa: F401
    from app.certificates import models as certificate_models  # noqa: F401
    from app.ctf import models as ctf_models  # noqa: F401
    from app.labs import models as labs_models  # noqa: F401
    from app.resources import models as resources_models  # noqa: F401


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

    @app.cli.command("seed-quizzes")
    def seed_quizzes_command() -> None:
        """Seed one quiz per module (idempotent — safe to re-run)."""
        from app.roadmap.quiz_seed import seed_quizzes

        result = seed_quizzes()
        if result["created"]:
            print("Quizzes seeded successfully.")
        else:
            print("Quizzes already populated — no changes made.")
        print(f"  quizzes:   {result['quizzes']}")
        print(f"  questions: {result['questions']}")
        print(f"  options:   {result['options']}")

    @app.cli.command("seed-achievements")
    def seed_achievements_command() -> None:
        """Seed achievement definitions (idempotent — safe to re-run)."""
        from app.achievement.seed import seed_achievements

        result = seed_achievements()
        if result["created"]:
            print("Achievements seeded successfully.")
        else:
            print("Achievements already populated — no changes made.")
        print(f"  achievements: {result['achievements']}")

    @app.cli.command("seed-certificates")
    def seed_certificates_command() -> None:
        """Seed certificate definitions (idempotent — safe to re-run)."""
        from app.certificates.seed import seed_certificates

        result = seed_certificates()
        if result["created"]:
            print("Certificates seeded successfully.")
        else:
            print("Certificates already populated — no changes made.")
        print(f"  certificates: {result['certificates']}")

    @app.cli.command("seed-ctf")
    def seed_ctf_command() -> None:
        """Seed CTF categories and challenges (idempotent — safe to re-run)."""
        from app.ctf.seed import seed_ctf

        result = seed_ctf()
        if result["created"]:
            print("CTF seeded successfully.")
        else:
            print("CTF already populated — no changes made.")
        print(f"  categories: {result['categories']}")
        print(f"  challenges: {result['challenges']}")
        print(f"  hints:      {result['hints']}")

    @app.cli.command("seed-labs")
    def seed_labs_command() -> None:
        """Seed lab categories, labs, objectives and files (idempotent)."""
        from app.labs.seed import seed_labs

        result = seed_labs()
        if result["created"]:
            print("Labs seeded successfully.")
        else:
            print("Labs already populated — no changes made.")
        print(f"  categories: {result['categories']}")
        print(f"  labs:       {result['labs']}")
        print(f"  objectives: {result['objectives']}")
        print(f"  files:      {result['files']}")
        if result.get("fs_nodes") is not None:
            print(f"  fs nodes:   {result['fs_nodes']}")

    @app.cli.command("seed-resources")
    def seed_resources_command() -> None:
        """Seed resource categories and articles (idempotent)."""
        from app.resources.seed import seed_resources

        result = seed_resources()
        if result["created"]:
            print("Resources seeded successfully.")
        else:
            print("Resources already populated — no changes made.")
        print(f"  categories: {result['categories']}")
        print(f"  resources:  {result['resources']}")
