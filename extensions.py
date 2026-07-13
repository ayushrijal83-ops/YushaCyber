"""Backward-compatibility shim.

Extensions moved into the application package in YC-004.2:
use ``from app.extensions import db, login_manager, csrf``.
This shim keeps any older imports working and will be removed
once nothing references the project-root location.
"""

from app.extensions import csrf, db, login_manager  # noqa: F401
