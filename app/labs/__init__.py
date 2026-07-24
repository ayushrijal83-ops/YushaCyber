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
from app.labs import network_simulator  # noqa: E402,F401  (YC-013.0)
from app.labs import interactive_network_simulator  # noqa: E402,F401  (YC-026.0)
from app.labs import web_security_simulator  # noqa: E402,F401  (YC-029.0)
from app.labs import soc_simulator  # noqa: E402,F401  (YC-030.0)
from app.labs.ad import simulator as ad_simulator  # noqa: E402,F401  (YC-031.0)
from app.labs.cloud import simulator as cloud_simulator  # noqa: E402,F401  (YC-032.0)
from app.labs.forensics import simulator as forensics_simulator  # noqa: E402,F401  (YC-029.5.2)
from app.simulators.soc import simulator as soc_simulator  # noqa: E402,F401  (YC-030.1)
# from app.labs import nmap_simulator     # future
# from app.labs import wireshark_simulator  # future
