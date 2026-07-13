"""Cyber Labs package (YC-011.1).

Models, service layer, seed, and a thin blueprint. Foundation only — no
terminal, container, command execution, scoring, or UI logic.
"""

from flask import Blueprint

labs_bp = Blueprint("labs", __name__)

from app.labs import routes  # noqa: E402,F401  (attach routes to the blueprint)

# --- Simulator plugin registration -----------------------------------------
# EXTENSION POINT: import each simulator module once so its @register_simulator
# decorator runs. Adding a lab type = add one import line here + its plugin file.
from app.labs import linux_simulator  # noqa: E402,F401
# from app.labs import nmap_simulator     # future
# from app.labs import wireshark_simulator  # future
