"""CTF (Capture The Flag) package.

Models, service layer, and seed (YC-010.1) plus the challenge browser
blueprint (YC-010.2).
"""

from flask import Blueprint

ctf_bp = Blueprint("ctf", __name__)

from app.ctf import routes  # noqa: E402,F401  (attach routes to the blueprint)
