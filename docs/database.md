# Database Workflow — YushaCyber

YushaCyber manages its database schema **exclusively through Flask-Migrate**
(Alembic). `db.create_all()` is not used anywhere in the project and must not
be reintroduced.

## Why Flask-Migrate

`db.create_all()` can only create tables that don't exist — it cannot add a
column, rename a field, change a type, or add an index to a table that already
holds data. That works for a throwaway prototype and silently fails for
everything after it. Migrations solve this: every schema change is a
versioned, reviewable script that can upgrade any database — a teammate's
laptop, CI, staging, production — from whatever revision it's on to the
current one, and roll back if needed. The migration history in
`migrations/versions/` is part of the codebase and is committed to git.

## One-time setup (new machine / fresh clone)

```bash
pip install -r requirements.txt
cp .env.example .env        # then set a real SECRET_KEY
flask --app app db upgrade  # builds instance/yushacyber.db from migrations
python app/app.py           # run the server
```

The application no longer creates tables on startup. If you skip
`flask db upgrade`, the homepage will still load (it doesn't touch the
database) but registration and login will fail with "no such table" —
that's your cue to run the upgrade.

## Making a schema change

1. Edit the model (e.g. add a column in `app/auth/models.py`, or create a
   new model in a feature package inheriting from `app.models.BaseModel`).
2. Make sure the model's module is imported by the app (new model modules
   get added to `_register_models()` in `app/__init__.py`).
3. Generate the migration and **read it before applying** — autogenerate is
   good but not infallible (it can miss server defaults and constraint
   subtleties, especially on SQLite):

   ```bash
   flask --app app db migrate -m "add badge table"
   ```

4. Apply it:

   ```bash
   flask --app app db upgrade
   ```

5. Commit the model change **and** the new file in `migrations/versions/`
   together in the same commit.

## Everyday commands

| Command | Purpose |
| --- | --- |
| `flask --app app db upgrade` | Apply all pending migrations |
| `flask --app app db migrate -m "msg"` | Autogenerate a migration from model changes |
| `flask --app app db current` | Show the revision the DB is on |
| `flask --app app db history` | List all revisions |
| `flask --app app db downgrade -1` | Roll back one revision |
| `flask --app app db stamp head` | Mark an existing DB as current **without** running migrations |

## New models: use BaseModel

Every table inherits `id`, `created_at` and `updated_at` (timezone-aware
UTC, auto-set and auto-updated) from the shared abstract base:

```python
from app.extensions import db
from app.models import BaseModel

class Badge(BaseModel):
    __tablename__ = "badges"
    name = db.Column(db.String(80), unique=True, nullable=False)
```

Don't redeclare `id` or the timestamp columns in concrete models.

## Rules

- **Never** call `db.create_all()` — not in app code, not in scripts, not
  "just this once" in a shell.
- Never edit an already-applied migration; create a new one instead.
- One logical schema change per migration, with a descriptive `-m` message.
- `instance/` (the SQLite file) is gitignored local state; `migrations/` is
  versioned source. Deleting `instance/yushacyber.db` is always safe in
  development — rebuild it with `flask --app app db upgrade`.

## Troubleshooting

**"no such table: users"** — you haven't run `flask --app app db upgrade`.

**"table users already exists" during upgrade** — the database predates the
migration history (it was made by the old `create_all()` flow). Either delete
`instance/yushacyber.db` and upgrade fresh, or run
`flask --app app db stamp head` once to adopt it.

**`flask db migrate` says "No changes in schema detected"** — the models
match the database; there's nothing to generate.
