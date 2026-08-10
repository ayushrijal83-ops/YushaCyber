"""Simulated web application — YC-035.0 Web Fundamentals.

Independent from network.py (network state) and packets.py (packet
traffic) — this module simulates HTTP request/response exchanges against
one fictional training site ("CyberShop"). Like both of those, it is pure
in-memory data and string formatting: this module makes zero real network
requests, ever, to any host, real or otherwise. There is no outbound HTTP
client here at all (no `requests`, no `urllib.request`, no `http.client`,
no socket) — only `urllib.parse`, which is pure string parsing (splitting
a URL into pieces) and never opens a connection.

A request to any host other than the simulated one is rejected before it
would ever reach this module (see commands.py's `open`/`request`
handlers) — there is structurally nothing here that *could* make an
outbound call even if that check were bypassed.
"""

from __future__ import annotations

import dataclasses
import html
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlsplit

HOST = "cybershop.training"
SERVER_HEADER = "CyberShop-Sim/1.0"

# Training-only credentials — never real accounts.
_USERS = {"student": "training123", "analyst": "analyst123", "admin": "admin123"}

# Fixed training bearer token for the Authorization-header objective
# (YC-035.1) — a single, deterministic value, never a real secret.
API_TOKEN = "training-token-001"

# ── SQL Injection Fundamentals (YC-035.4) — fixed, fictional training
# catalog for /search and /secure-search. Never real product data. ──
PRODUCTS: list[dict[str, Any]] = [
    {"id": 1, "name": "Laptop", "price": 999, "category": "Electronics"},
    {"id": 2, "name": "Keyboard", "price": 49, "category": "Electronics"},
    {"id": 3, "name": "Monitor", "price": 199, "category": "Electronics"},
    {"id": 4, "name": "Mouse", "price": 25, "category": "Electronics"},
]

# Read-only, fictional schema for the Database Inspector panel/'schema'
# command — structure only, no row data, so nothing here could ever look
# like a real data dump.
DB_SCHEMA: dict[str, list[tuple[str, str]]] = {
    "users": [("id", "INTEGER"), ("username", "TEXT"), ("role", "TEXT")],
    "products": [("id", "INTEGER"), ("name", "TEXT"), ("price", "INTEGER"),
                 ("category", "TEXT")],
    "orders": [("id", "INTEGER"), ("user_id", "INTEGER"),
               ("product_id", "INTEGER"), ("quantity", "INTEGER")],
    "reviews": [("id", "INTEGER"), ("product_id", "INTEGER"),
                ("username", "TEXT"), ("rating", "INTEGER")],
    # Added for XSS Fundamentals (YC-035.5) — the feedback/comment store.
    "comments": [("id", "INTEGER"), ("author", "TEXT"), ("content", "TEXT"),
                 ("created_at", "TEXT")],
}

# Fixed, deterministic training payloads (YC-035.4). The simulator never
# executes student-supplied text as SQL — '_classify_query_pattern' and
# '_classify_login_pattern' below only ever compare the input against
# these exact strings, then return one of a handful of pre-written,
# canned responses. There is no SQL parser or SQL engine anywhere in this
# module, so nothing outside this fixed set can change simulator
# behavior — an arbitrary/unexpected string is always just 'normal'
# (treated as a literal search term or a literal, wrong, username).
TRAINING_TRUE_PAYLOAD = "' OR '1'='1"
TRAINING_FALSE_PAYLOAD = "' AND '1'='2"
TRAINING_ERROR_PAYLOAD = "'"
TRAINING_COMMENT_PAYLOAD = "' --"
TRAINING_UNION_PAYLOAD = "' UNION SELECT NULL, NULL --"
TRAINING_AUTH_BYPASS_USERNAME = "admin'--"

# Fixed, deterministic training markers for XSS Fundamentals (YC-035.5) —
# same discipline as the SQLi payloads above: 'has_xss_marker' only ever
# compares input against this exact, fixed set of strings, case-
# insensitively. There is no HTML/JS parser anywhere in this module and
# nothing here is ever rendered by a real browser or executed as
# JavaScript — an unrecognized, even realistic-looking, XSS-shaped string
# (e.g. "<img src=x onerror=alert(1)>") is never treated specially; it is
# just literal text, exactly like any other search term or comment.
TRAINING_XSS_MARKERS = (
    "<TRAINING_XSS>",
    "<TRAINING_ALERT>",
    "<TRAINING_MARKER>",
    "<script>TRAINING_XSS</script>",
)

# A realistic-looking but fixed, non-secret Content-Security-Policy value
# (YC-035.5) — informational only; nothing in this simulator enforces it
# against anything, since no real script ever runs here regardless.
CSP_POLICY = "default-src 'self'; script-src 'self'"

# ── Cross-Site Request Forgery Fundamentals (YC-035.6) — fixed, fictional
# training constants. Balances are training-only in-memory integers on a
# single WebApp instance; never a real financial system, never persisted
# anywhere real. TRUSTED_ORIGIN/ATTACKER_ORIGIN are plain string values a
# terminal command can set via 'open -H "Origin: ..."' (see commands.py) —
# there is no second host or real cross-origin request anywhere in this
# module; "Origin" here is just a request header the simulator inspects,
# exactly like any other header.
TRANSFER_RECIPIENT = "training-user"
STARTING_BALANCE = 5000
TRUSTED_ORIGIN = f"https://{HOST}"
ATTACKER_ORIGIN = "https://attacker.training"


def _csrf_token_for_session(sid: str) -> str:
    """Deterministic, session-bound training CSRF token (YC-035.6) — not
    a cryptographic secret, just a fixed, reproducible string derived
    from the session id, so the Token panel and the mission validator
    can both compute/verify it independently, with no hidden random
    state. Same discipline as API_TOKEN: fixed and reproducible, never
    actually random."""
    return "TRAINING_TOKEN_" + sid.upper().replace("-", "_")


# ── File Upload Security Fundamentals (YC-035.7) — fixed, fictional
# training file catalog for /upload and /secure-upload. There is no real
# file I/O or byte content anywhere in this module: an upload "request"
# is always a small set of explicit, client-supplied fields (filename,
# claimed content_type, claimed size, and a fixed 'signature' label
# standing in for detected magic bytes) — the same "no real parser, only
# fixed classification of explicit fields" discipline as the SQLi/XSS
# payload constants above. Nothing here ever reads, writes, or executes
# a real file.
TRAINING_FILES: dict[str, dict[str, Any]] = {
    "avatar.jpg": {"mime": "image/jpeg", "signature": "JPEG", "size": 24_000},
    "avatar.png": {"mime": "image/png", "signature": "PNG", "size": 51_000},
    "avatar.gif": {"mime": "image/gif", "signature": "GIF", "size": 12_000},
    "document.pdf": {"mime": "application/pdf", "signature": "PDF", "size": 102_000},
    "notes.txt": {"mime": "text/plain", "signature": "TEXT", "size": 1_200},
    "training-marker.svg": {"mime": "image/svg+xml", "signature": "SVG", "size": 3_400},
    # A fixed, fictional 'disguised executable' training file — labeled
    # "training-executable-marker" in the UI (YC-035.7 §18) — an image
    # *extension* whose detected signature is EXECUTABLE, so the
    # vulnerable (extension-only) pipeline accepts it while the secure
    # (signature-checking) pipeline blocks it. Never a real executable;
    # 'signature' is only ever a fixed classification label, never
    # parsed, compiled, or run.
    "shell.jpg": {"mime": "image/jpeg", "signature": "EXECUTABLE", "size": 8_000},
    "oversized.jpg": {"mime": "image/jpeg", "signature": "JPEG", "size": 3_000_000},
    "mismatched.jpg": {"mime": "text/plain", "signature": "TEXT", "size": 2_000},
}

EXPECTED_MIME_FOR_EXTENSION: dict[str, str] = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".pdf": "application/pdf", ".txt": "text/plain",
    ".svg": "image/svg+xml",
}
EXPECTED_SIGNATURE_FOR_EXTENSION: dict[str, str] = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".gif": "GIF",
    ".pdf": "PDF", ".txt": "TEXT", ".svg": "SVG",
}
_SIGNATURE_CATEGORY: dict[str, str] = {
    "JPEG": "image", "PNG": "image", "GIF": "image", "SVG": "image",
    "PDF": "document", "TEXT": "text", "EXECUTABLE": "executable",
}

# The vulnerable pipeline validates only the filename's extension — an
# image-only-looking allowlist that still includes '.svg' (a real-world
# mistake: SVG can carry embedded scripts). The secure pipeline's
# allowlist deliberately excludes '.svg' for that reason.
VULNERABLE_UPLOAD_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".svg"})
SECURE_UPLOAD_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif"})
UPLOAD_SIZE_LIMIT_BYTES = 2_000_000  # 2 MB, fixed training limit


def _extension_of(filename: str) -> str:
    """Pure string split — the last '.'-separated suffix, lowercased.
    No filesystem access, no path resolution."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[1].lower()


def _looks_like_path_traversal(filename: str) -> bool:
    """A fixed, conceptual path-traversal detector (YC-035.7) — pure
    substring checks, never real path resolution. Since this module has
    no filesystem access anywhere, a traversal-shaped filename could
    never actually escape anything even without this check; it exists
    purely so the secure pipeline can demonstrably reject the shape,
    the same "prove the defense, don't just assert it" discipline as
    every other secure endpoint in this file."""
    return ".." in filename or filename.startswith("/") or "\\" in filename


def _category_for_signature(signature: str) -> str:
    return _SIGNATURE_CATEGORY.get(signature, "unknown")


def has_xss_marker(text: str) -> bool:
    """True if `text` is *exactly* one of the fixed training markers
    above (YC-035.5), case-insensitively. Public (unlike the SQLi
    classifiers) because mission_validator.py never needs it — every XSS
    validator check reads the structured 'X-Sim-XSS-Kind' response header
    this module already sets, not raw text — but commands.py's
    '_track_xss_response' and this module's own route handlers both need
    it, so it lives here once rather than being duplicated."""
    s = text.strip().lower()
    return any(s == m.lower() for m in TRAINING_XSS_MARKERS)


def _simulated_xss_panel(source: str, sink: str) -> str:
    """The 'SIMULATED BROWSER EVENT' box (YC-035.5) — pure text
    formatting appended to a response body when a training marker
    reaches a simulated sink. Never a real DOM event, never real
    JavaScript — the disclaimer line says so explicitly, every time."""
    return (
        "┌─────────────────────────────────┐\n"
        "│ SIMULATED BROWSER EVENT          │\n"
        "├─────────────────────────────────┤\n"
        "│ XSS marker detected              │\n"
        "└─────────────────────────────────┘\n"
        f"Source: {source}\n"
        f"Sink: {sink}\n"
        "Result: simulated execution\n"
        "Simulation only — no JavaScript executed in YushaCyber."
    )


@dataclass
class Comment:
    """A single stored training comment (YC-035.5) — 'sink' records
    whether it was submitted through the vulnerable or secure feedback
    endpoint, so /comments can render each one according to its own
    origin without a second storage table."""
    id: int
    author: str
    content: str
    sink: str  # "vulnerable" | "secure"
    created_at: str = "simulated"


@dataclass
class Transfer:
    """A single simulated funds transfer (YC-035.6) — mirrors Comment:
    small, explicit, in-memory only. 'defense' records which endpoint
    handled it (vulnerable /transfer, no CSRF check, vs. secure
    /secure-transfer, token-verified), for the Transfer History page and
    the evidence checklist. Never a real financial system."""
    id: int
    sender: str
    recipient: str
    amount: int
    defense: str  # "vulnerable" | "secure"
    created_at: str = "simulated"


@dataclass
class UploadedFile:
    """A single simulated upload (YC-035.7) — mirrors Transfer/Comment:
    small, explicit, in-memory only. 'pipeline' records which endpoint
    stored it (vulnerable /upload, extension-only, vs. secure
    /secure-upload, fully validated) so the Uploads list and the
    vulnerable-vs-secure comparison can render each one according to its
    own origin. Never real file bytes, never a real filesystem path."""
    id: str
    owner: str
    original_filename: str
    stored_name: str
    extension: str
    mime: str
    signature: str
    size: int
    category: str
    pipeline: str  # "vulnerable" | "secure"
    web_accessible: bool
    created_at: str = "simulated"


@dataclass
class ParsedUrl:
    scheme: str
    host: str
    port: int
    path: str
    query: dict[str, str]
    fragment: str


def parse_url(url: str) -> ParsedUrl:
    """Split a URL into its components — pure string parsing, no I/O."""
    parts = urlsplit(url)
    scheme = parts.scheme or "https"
    host = parts.hostname or ""
    port = parts.port or (443 if scheme == "https" else 80)
    path = parts.path or "/"
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    return ParsedUrl(scheme=scheme, host=host, port=port, path=path,
                     query=query, fragment=parts.fragment or "")


def _parse_form(body: str) -> dict[str, str]:
    return dict(parse_qsl(body))


def parse_body(body: str, content_type: str) -> dict[str, Any]:
    """Parse a request/response body into a dict, per its Content-Type
    (YC-035.1) — pure parsing, mirrors _parse_form for JSON. Used by the
    'body_field' validator check so objectives can inspect a specific
    JSON/form field instead of substring-matching raw text."""
    if not body:
        return {}
    ct = (content_type or "").lower()
    if "json" in ct:
        try:
            data = json.loads(body)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return _parse_form(body)


def _classify_query_pattern(q: str) -> str:
    """Classifies a 'q' search value into one of a fixed set of training
    outcomes (YC-035.4) — pure string equality against the constants
    above, case-insensitive. Never parses or executes the input as SQL;
    anything that isn't an exact match to a known training payload is
    just 'normal' (a literal search term)."""
    s = q.strip().lower()
    if s == TRAINING_ERROR_PAYLOAD.lower():
        return "error"
    if s == TRAINING_TRUE_PAYLOAD.lower():
        return "boolean_true"
    if s == TRAINING_FALSE_PAYLOAD.lower():
        return "boolean_false"
    if s == TRAINING_COMMENT_PAYLOAD.lower():
        return "comment"
    if s == TRAINING_UNION_PAYLOAD.lower():
        return "union"
    return "normal"


def _classify_login_pattern(username: str) -> str:
    """Classifies a training-login username (YC-035.4) — same discipline
    as _classify_query_pattern: one fixed, fictional payload, compared by
    exact string equality, never parsed or executed as SQL."""
    if username.strip().lower() == TRAINING_AUTH_BYPASS_USERNAME.lower():
        return "auth_bypass"
    return "normal"


def _search_query_repr(q: str) -> str:
    """The 'Application Query' shown by the query visualizer for the
    *vulnerable* /search endpoint — literal, unsafe string concatenation,
    so the training payload's quotes/keywords visibly become part of the
    query text. Text formatting only; never actually executed."""
    return f"SELECT * FROM products WHERE name = '{q}'"


def _secure_search_query_repr() -> str:
    """The /secure-search counterpart — always this exact, fixed string,
    regardless of input: a parameterized query's *structure* never
    changes, no matter what the student types."""
    return "SELECT * FROM products WHERE name = ?"


def _login_query_repr(username: str) -> str:
    return f"SELECT * FROM users WHERE username = '{username}' AND password = '***'"


def _secure_login_query_repr() -> str:
    return "SELECT * FROM users WHERE username = ? AND password = ?"


@dataclass
class HttpRequest:
    method: str
    scheme: str
    host: str
    port: int
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: str = ""
    timestamp: float = 0.0


@dataclass
class HttpResponse:
    status_code: int
    reason: str
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    # Cookie names the response tells the browser to delete (YC-035.3 —
    # logout). Kept separate from `cookies` (which only ever holds
    # *set* values) so render_response can emit the real
    # `Set-Cookie: name=; Max-Age=0` deletion form, and WebSession.record
    # can drop the name from its jar — the same distinction a real
    # browser makes between "set this cookie" and "delete this cookie".
    deleted_cookies: list[str] = field(default_factory=list)
    body: str = ""
    content_type: str = "text/plain"
    server: str = SERVER_HEADER


def build_request(method: str, url: ParsedUrl, body: str = "",
                  cookies: dict[str, str] | None = None,
                  timestamp: float = 0.0,
                  extra_headers: dict[str, str] | None = None) -> HttpRequest:
    headers = {
        "Host": url.host,
        "User-Agent": "YushaCyber-Trainer/1.0",
        "Accept": "*/*",
    }
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Content-Length"] = str(len(body))
    if extra_headers:
        # Applied after the defaults so a caller can override Content-Type
        # (e.g. to send JSON) or add Authorization/Referer (YC-035.1) —
        # the same curl-like '-H' mechanism a real HTTP client offers.
        headers.update(extra_headers)
        if body:
            headers["Content-Length"] = str(len(body))
    return HttpRequest(method=method.upper(), scheme=url.scheme, host=url.host,
                       port=url.port, path=url.path, query=dict(url.query),
                       headers=headers, cookies=dict(cookies or {}), body=body,
                       timestamp=timestamp)


class WebApp:
    """The simulated CyberShop training site. Routes are plain Python
    control flow over deterministic canned responses — never a real
    server, never a real socket."""

    def __init__(self, sessions: dict[str, str] | None = None,
                 profiles: dict[str, dict[str, Any]] | None = None,
                 comments: list[Comment] | None = None,
                 balances: dict[str, int] | None = None,
                 transfers: list[Transfer] | None = None,
                 uploads: list[UploadedFile] | None = None) -> None:
        # session_id -> username. Mutated by successful logins/logouts,
        # exactly like VirtualNetwork's interface state (YC-034.6) —
        # small, explicit, session-scoped state.
        self.sessions: dict[str, str] = dict(sessions) if sessions else {}
        # username -> profile fields (YC-035.2) — mirrors self.sessions:
        # small, explicit, mutable, in-memory only. Lets POST /api/profile
        # have a real, observable effect instead of a no-op acknowledgment,
        # so proxy request-modification objectives have something genuine
        # to verify.
        self.profiles: dict[str, dict[str, Any]] = (
            dict(profiles) if profiles else {})
        # Stored training feedback (YC-035.5) — mirrors self.profiles:
        # small, explicit, mutable, in-memory only. Populated by POST
        # /feedback and /secure-feedback, rendered by GET /comments.
        self.comments: list[Comment] = list(comments) if comments else []
        # Training account balances (YC-035.6) — username -> integer
        # balance, lazily defaulted to STARTING_BALANCE via _balance()
        # rather than pre-populated, mirroring self.profiles's
        # setdefault-on-first-use pattern. Never a real financial system.
        self.balances: dict[str, int] = dict(balances) if balances else {}
        # Simulated funds transfers (YC-035.6) — mirrors self.comments:
        # small, explicit, mutable, in-memory only. Populated by POST
        # /transfer and /secure-transfer, rendered by GET /transfer-history.
        self.transfers: list[Transfer] = list(transfers) if transfers else []
        # Simulated uploads (YC-035.7) — mirrors self.transfers: small,
        # explicit, mutable, in-memory only. Populated by POST /upload
        # and /secure-upload, rendered by GET /uploads and GET
        # /upload/<id>. Never real file bytes, never a real filesystem
        # write — 'stored_name' is just a string label.
        self.uploads: list[UploadedFile] = list(uploads) if uploads else []

    def _random_stored_name(self, extension: str) -> str:
        """Deterministic, reproducible 'random-looking' stored filename
        (YC-035.7) — never real randomness, matching this module's
        established discipline (the fixed CSRF token, the fixed SQLi/XSS
        payload constants) so the UI and tests can predict it exactly.
        Derived only from how many uploads already exist, the same
        'id = len(list) + 1' counting pattern Comment/Transfer already
        use — no separate counter field needed."""
        digest = ((len(self.uploads) + 1) * 2654435761) & 0xFFFFFFFF
        return f"{digest:08x}{extension}"

    def _balance(self, username: str) -> int:
        """Every real training user (student/analyst/admin) starts at
        STARTING_BALANCE; the fictional transfer recipient starts at 0 —
        matching the mission's documented starting state (student:
        $5,000, training recipient: $0). A username already recorded in
        self.balances (because a transfer touched it) always wins."""
        if username in self.balances:
            return self.balances[username]
        return 0 if username == TRANSFER_RECIPIENT else STARTING_BALANCE

    def handle(self, req: HttpRequest) -> HttpResponse:
        """Dispatches to a route handler, then applies the one
        cross-cutting concern every response shares (YC-035.5): a fixed,
        informational Content-Security-Policy header. Centralized here so
        every current and future route gets it automatically instead of
        every handler repeating it."""
        resp = self._route(req)
        resp.headers.setdefault("Content-Security-Policy", CSP_POLICY)
        return resp

    def _route(self, req: HttpRequest) -> HttpResponse:
        if req.path == "/" and req.method == "GET":
            return self._ok("Welcome to CyberShop — a simulated training storefront.")
        if req.path == "/products" and req.method == "GET":
            return self._products(req)
        if req.path == "/search" and req.method == "GET":
            return self._search(req)
        if req.path == "/secure-search" and req.method == "GET":
            return self._secure_search(req)
        if req.path == "/training-login" and req.method == "POST":
            return self._training_login(req)
        if req.path == "/secure-login" and req.method == "POST":
            return self._secure_login(req)
        if req.path == "/feedback" and req.method == "GET":
            return self._feedback_get(req)
        if req.path == "/feedback" and req.method == "POST":
            return self._feedback_post(req, sink="vulnerable")
        if req.path == "/secure-feedback" and req.method == "POST":
            return self._feedback_post(req, sink="secure")
        if req.path == "/comments" and req.method == "GET":
            return self._comments_get(req)
        if req.path == "/dom-demo" and req.method == "GET":
            return self._dom_demo_get(req)
        if req.path == "/login" and req.method == "GET":
            return self._redirect("/auth/login")
        if req.path == "/auth/login" and req.method == "GET":
            return self._ok("Please log in with your training account.")
        if req.path in ("/login", "/auth/login") and req.method == "POST":
            return self._login(req)
        if req.path == "/profile" and req.method == "GET":
            return self._profile(req)
        # POST /logout added alongside the existing GET /logout (YC-035.3)
        # — the actual training login/logout flow submits a form via POST;
        # GET stays for backward compatibility with earlier missions.
        if req.path == "/logout" and req.method in ("GET", "POST"):
            return self._logout(req)
        if req.path == "/account" and req.method == "GET":
            return self._account(req)
        if req.path == "/settings" and req.method == "GET":
            return self._settings(req)
        if req.path == "/csrf-demo" and req.method == "GET":
            return self._csrf_demo(req)
        if req.path == "/secure-transfer" and req.method == "GET":
            return self._secure_transfer_page(req)
        if req.path == "/transfer" and req.method == "POST":
            return self._transfer(req, defense="vulnerable")
        if req.path == "/secure-transfer" and req.method == "POST":
            return self._transfer(req, defense="secure")
        if req.path == "/transfer-history" and req.method == "GET":
            return self._transfer_history(req)
        if req.path == "/upload" and req.method == "GET":
            return self._upload_get(req)
        if req.path == "/upload" and req.method == "POST":
            return self._upload_post(req, pipeline="vulnerable")
        if req.path == "/secure-upload" and req.method == "GET":
            return self._secure_upload_get(req)
        if req.path == "/secure-upload" and req.method == "POST":
            return self._upload_post(req, pipeline="secure")
        if req.path == "/uploads" and req.method == "GET":
            return self._uploads_list(req)
        if req.path == "/upload-security" and req.method == "GET":
            return self._upload_security_page(req)
        # GET /upload/<id> (YC-035.7) — the "controlled download handler":
        # a dynamic segment, handled as a plain string prefix check (this
        # simulator has no routing framework — every other route above is
        # an exact path match) rather than a real path-parameter parser.
        if (req.method == "GET" and req.path.startswith("/upload/")
                and req.path != "/upload/"):
            return self._upload_detail(req, req.path[len("/upload/"):])
        if req.path == "/dashboard" and req.method == "GET":
            return self._dashboard(req)
        if req.path == "/admin" and req.method == "GET":
            return self._admin(req)
        if req.path == "/api/login" and req.method == "POST":
            return self._api_login(req)
        if req.path == "/api/profile" and req.method in ("GET", "POST"):
            return self._api_profile(req)
        if req.path == "/api/me" and req.method == "GET":
            return self._api_me(req)
        return self._not_found()

    def _products(self, req: HttpRequest) -> HttpResponse:
        pid = req.query.get("id")
        if pid:
            body = f"Product #{pid}: Sample training item."
            # Deterministic cache metadata (YC-035.1) — a fixed value, not a
            # real cache engine; "do NOT implement a complex cache engine...
            # a deterministic simulated response is enough".
            headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                      "Server": SERVER_HEADER, "Cache-Control": "max-age=60",
                      "ETag": f'"product-{pid}-v1"',
                      "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"}
            return HttpResponse(status_code=200, reason="OK", body=body,
                                content_type="text/html", headers=headers)
        return self._ok("Product catalog: 3 items available.")

    def _render_products(self, q: str, matches: list[dict[str, Any]], note: str) -> str:
        lines = [f"Search results for '{q}': {len(matches)} match(es) in the training catalog."]
        for p in matches:
            lines.append(f"  - {p['name']} (${p['price']})")
        if note:
            lines.append("")
            lines.append(note)
        return "\n".join(lines)

    def _search(self, req: HttpRequest) -> HttpResponse:
        """The intentionally vulnerable training search endpoint
        (YC-035.4). Internally represents an unsafe, string-concatenated
        query — conceptually `SELECT * FROM products WHERE name =
        '<input>'` — but never actually builds or runs that string as
        SQL. `_classify_query_pattern` only ever compares 'q' against a
        fixed set of exact training payloads; every branch below returns
        a predetermined, deterministic outcome. An unrecognized string is
        always just a literal (safe) substring search over the fixed
        PRODUCTS catalog."""
        q = req.query.get("q", "")
        kind = _classify_query_pattern(q)
        query_repr = _search_query_repr(q)
        # XSS reflection (YC-035.5) — independent of the SQLi kind above;
        # both concerns coexist on the same endpoint via separate headers.
        xss_kind = "reflected" if has_xss_marker(q) else "none"
        base_headers = {"X-Sim-Query-Kind": kind, "X-Sim-Query": query_repr,
                        "X-Sim-XSS-Kind": xss_kind, "X-Sim-XSS-Context": "html_text"}

        if kind == "error":
            body = "Database error: Unexpected quote in training query."
            headers = {"Content-Type": "text/plain", "Content-Length": str(len(body)),
                      "Server": SERVER_HEADER, **base_headers}
            return HttpResponse(status_code=500, reason="Internal Server Error", body=body,
                                content_type="text/plain", headers=headers)

        if kind == "boolean_true":
            matches = list(PRODUCTS)
            note = ("Simulated: the injected condition made the query's logic always "
                    "true, so every row matched — not a real, intentional search result.")
        elif kind == "boolean_false":
            matches = []
            note = ("Simulated: the injected condition made the query's logic always "
                    "false, so no rows matched.")
        elif kind in ("comment", "union"):
            matches = []
            note = ("Simulated: the injected input changed the query's structure "
                    "(conceptual demonstration only — no real data is ever returned here).")
        else:
            matches = ([p for p in PRODUCTS if q.strip().lower() in p["name"].lower()]
                      if q.strip() else [])
            note = ""

        body = self._render_products(q, matches, note)
        if xss_kind == "reflected":
            body += "\n\n" + _simulated_xss_panel(source="search?q=", sink="reflected HTML")
        headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store", **base_headers}
        return HttpResponse(status_code=200, reason="OK", body=body,
                            content_type="text/html", headers=headers)

    def _secure_search(self, req: HttpRequest) -> HttpResponse:
        """The parameterized-query counterpart to /search (YC-035.4): 'q'
        is always treated as literal data for a plain substring match —
        never classified, never able to change the query's structure or
        trigger an error/boolean/union outcome, no matter what's typed.
        The 'Application Query' this reports is always the exact same
        fixed string, which is the whole point students should observe."""
        q = req.query.get("q", "")
        matches = ([p for p in PRODUCTS if q.strip().lower() in p["name"].lower()]
                  if q.strip() else [])
        # Output encoding (YC-035.5): the value shown in the body is
        # HTML-escaped — '<'/'>'/etc. become '&lt;'/'&gt;'/etc. — so a
        # training marker is displayed as inert text, never as markup.
        escaped_q = html.escape(q, quote=True)
        body = self._render_products(escaped_q, matches, "")
        xss_kind = "encoded" if has_xss_marker(q) else "none"
        headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store",
                  "X-Sim-Query-Kind": "parameterized", "X-Sim-Query": _secure_search_query_repr(),
                  "X-Sim-XSS-Kind": xss_kind, "X-Sim-XSS-Context": "html_text"}
        return HttpResponse(status_code=200, reason="OK", body=body,
                            content_type="text/html", headers=headers)

    def _training_login(self, req: HttpRequest) -> HttpResponse:
        """The intentionally vulnerable training login (YC-035.4) —
        conceptually `SELECT * FROM users WHERE username = '<u>' AND
        password = '<p>'`, never actually built or run as SQL. Only the
        one fixed TRAINING_AUTH_BYPASS_USERNAME comment-style payload is
        recognized; everything else falls through to the same fixed
        credential check every other login endpoint uses."""
        creds = parse_body(req.body, req.headers.get("Content-Type", ""))
        username, password = creds.get("username", ""), creds.get("password", "")
        kind = _classify_login_pattern(username)
        query_repr = _login_query_repr(username)
        base_headers = {"X-Sim-Query-Kind": kind, "X-Sim-Query": query_repr}

        if kind == "auth_bypass":
            return self._json_ok(
                {"status": "success", "authenticated_as": "admin", "simulated": True,
                 "note": ("Simulated authentication bypass: a comment sequence in the "
                         "username removed the password check from the query entirely.")},
                extra_headers=base_headers)
        if username in _USERS and _USERS[username] == password:
            return self._json_ok({"status": "success", "authenticated_as": username},
                                 extra_headers=base_headers)
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Invalid training credentials"},
                                extra_headers=base_headers)

    def _secure_login(self, req: HttpRequest) -> HttpResponse:
        """Parameterized-query counterpart to /training-login (YC-035.4):
        username/password are always compared as literal data, so the
        one fixed bypass payload above fails here exactly like any other
        wrong username — proving the defense, not just asserting it."""
        creds = parse_body(req.body, req.headers.get("Content-Type", ""))
        username, password = creds.get("username", ""), creds.get("password", "")
        base_headers = {"X-Sim-Query-Kind": "parameterized", "X-Sim-Query": _secure_login_query_repr()}
        if username in _USERS and _USERS[username] == password:
            return self._json_ok({"status": "success", "authenticated_as": username},
                                 extra_headers=base_headers)
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Invalid training credentials"},
                                extra_headers=base_headers)

    def _feedback_get(self, req: HttpRequest) -> HttpResponse:
        body = ("Submit training feedback:\n"
               "POST /feedback (vulnerable) or POST /secure-feedback (secure) with "
               "'name' and 'comment' form fields.\n"
               "View stored comments at GET /comments.")
        return self._ok(body, content_type="text/plain")

    def _feedback_post(self, req: HttpRequest, sink: str) -> HttpResponse:
        """Stores a training comment (YC-035.5) — 'sink' distinguishes
        the vulnerable endpoint (rendered raw by /comments, later) from
        the secure one (always rendered HTML-escaped). The vulnerable
        submission's own response never shows a simulated execution
        panel — that only appears when the comment is later *rendered*
        by GET /comments, preserving the reflected-vs-stored distinction
        (immediate vs. delayed). The secure endpoint's encoding is
        provable immediately, since nothing unsafe ever happens either way."""
        data = parse_body(req.body, req.headers.get("Content-Type", ""))
        author = data.get("name", "anonymous")
        content = data.get("comment", "")
        comment = Comment(id=len(self.comments) + 1, author=author,
                          content=content, sink=sink,
                          created_at=f"training-entry-{len(self.comments) + 1}")
        self.comments.append(comment)
        if sink == "secure":
            kind = "encoded" if has_xss_marker(content) else "none"
        else:
            kind = "stored" if has_xss_marker(content) else "none"
        return self._json_ok({"status": "stored", "id": comment.id, "sink": sink},
                             extra_headers={"X-Sim-XSS-Kind": kind})

    def _comments_get(self, req: HttpRequest) -> HttpResponse:
        lines = ["Stored training comments:"]
        stored_event = False
        if not self.comments:
            lines.append("  (no comments yet)")
        for c in self.comments:
            if c.sink == "vulnerable":
                lines.append(f"  #{c.id} {c.author}: {c.content}")
                if has_xss_marker(c.content):
                    stored_event = True
                    lines.append("")
                    lines.append(_simulated_xss_panel(
                        source=f"stored comment #{c.id}", sink="rendered HTML (unsafe)"))
                    lines.append("")
            else:
                escaped = html.escape(c.content, quote=True)
                lines.append(f"  #{c.id} {c.author}: {escaped} (HTML-escaped)")
        body = "\n".join(lines)
        kind = "stored" if stored_event else "none"
        headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store",
                  "X-Sim-XSS-Kind": kind, "X-Sim-XSS-Context": "html_text"}
        return HttpResponse(status_code=200, reason="OK", body=body,
                            content_type="text/html", headers=headers)

    def _dom_demo_get(self, req: HttpRequest) -> HttpResponse:
        """A conceptual DOM-XSS demo (YC-035.5): text describing a
        simulated client-side source->sink flow. No real JavaScript runs
        here — the 'processing'/'sink' lines are a description, not
        code, and the only thing that changes with 'input' is which
        branch of Python string formatting below executes."""
        user_input = req.query.get("input", "")
        triggered = has_xss_marker(user_input)
        lines = [
            "DOM XSS Demo (simulated client-side sink — no real JavaScript runs here)",
            "",
            "Source: the 'input' URL parameter (location.search)",
            "Processing: simulated client-side JavaScript reads the parameter",
            "Sink: simulated element.innerHTML assignment",
            f"Current input: {user_input or '(none)'}",
        ]
        if triggered:
            lines.append("")
            lines.append(_simulated_xss_panel(
                source="URL parameter 'input'", sink="simulated innerHTML DOM sink"))
        body = "\n".join(lines)
        kind = "dom" if triggered else "none"
        headers = {"Content-Type": "text/html", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store",
                  "X-Sim-XSS-Kind": kind, "X-Sim-XSS-Context": "dom"}
        return HttpResponse(status_code=200, reason="OK", body=body,
                            content_type="text/html", headers=headers)

    def _check_credentials(self, req: HttpRequest) -> str | None:
        """Returns the matched training username, or None if invalid.
        Shared by the form-based and JSON login endpoints — same
        credentials, two different wire formats (YC-035.1)."""
        creds = parse_body(req.body, req.headers.get("Content-Type", ""))
        username, password = creds.get("username", ""), creds.get("password", "")
        if username in _USERS and _USERS[username] == password:
            return username
        return None

    def _login(self, req: HttpRequest) -> HttpResponse:
        username = self._check_credentials(req)
        if username:
            sid = f"{username}-session"
            self.sessions[sid] = username
            resp = self._redirect("/profile")
            resp.cookies["session_id"] = sid
            return resp
        # JSON failure body (YC-035.3) — same 401 status YC-035.0 already
        # locked in (test_login_post_invalid_credentials), just a
        # structured body instead of plain text, matching real login APIs
        # and the training spec's exact error shape. Never echoes back
        # the submitted password or any other secret.
        return self._json_error(401, "Unauthorized",
                                {"error": "Invalid training credentials"})

    def _profile(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if username:
            return self._ok(f"Profile: {username}")
        return self._error(401, "Unauthorized", "You must log in to view this page.")

    def _account(self, req: HttpRequest) -> HttpResponse:
        """Cookie-protected page that redirects instead of erroring when
        unauthenticated (YC-035.3) — the browser-style counterpart to
        /profile's API-style 401, so students see both patterns real
        sites use for a "protected route"."""
        username = self._session_user(req)
        if username:
            return self._ok(f"Account settings for {username}.")
        return self._redirect("/login")

    def _settings(self, req: HttpRequest) -> HttpResponse:
        """Protected settings page (YC-035.6) — same cookie-protected,
        redirect-on-failure pattern as /account. Purely a navigation hub
        for the training pages this mission adds; carries no state of its
        own."""
        username = self._session_user(req)
        if not username:
            return self._redirect("/login")
        return self._ok(f"Settings for {username}. See /csrf-demo (vulnerable transfer) "
                        "and /secure-transfer (protected transfer).")

    def _csrf_demo(self, req: HttpRequest) -> HttpResponse:
        """Informational page describing the vulnerable transfer scenario
        (YC-035.6) — text only; visiting it never itself performs a
        transfer. Explains what POST /transfer does and why the
        browser's automatic cookie attachment is what lets a forged
        request through: the endpoint trusts the session cookie alone,
        with no check that the request was actually intended by the
        user."""
        body = (
            "CSRF Demo — Vulnerable Transfer\n\n"
            "POST /transfer moves simulated training funds between accounts. It is "
            "protected only by the session cookie: any request carrying a valid "
            "session_id cookie is accepted, with no check that the request was "
            "actually intended by the logged-in user.\n\n"
            "Example vulnerable request:\n"
            "POST /transfer\n"
            f"recipient={TRANSFER_RECIPIENT}\n"
            "amount=100\n\n"
            "A page on any other origin can auto-submit this same request; the "
            "student's browser still attaches their cybershop.training session "
            "cookie automatically, because that's how browsers handle cookies for "
            "requests to a given site, regardless of which page triggered them.\n\n"
            "Compare with the protected version at /secure-transfer, which "
            "additionally requires a csrf_token parameter and validates the "
            "request's Origin."
        )
        return self._ok(body, content_type="text/plain")

    def _secure_transfer_page(self, req: HttpRequest) -> HttpResponse:
        """GET /secure-transfer (YC-035.6) — shows the logged-in student
        their own session-bound training CSRF token, the exact value
        POST /secure-transfer verifies. Redirects to /login when
        unauthenticated, same pattern as /account."""
        username = self._session_user(req)
        if not username:
            return self._redirect("/login")
        sid = req.cookies.get("session_id", "")
        token = _csrf_token_for_session(sid)
        body = (
            f"Secure Transfer — logged in as {username}\n\n"
            f"csrf_token={token}\n\n"
            "Submit this token together with 'recipient' and 'amount' in a POST "
            "to /secure-transfer. Requests missing the token, or carrying the "
            "wrong one, are rejected with 403 Forbidden."
        )
        return self._ok(body, content_type="text/plain",
                        extra_headers={"X-Sim-CSRF-Token": token, "X-Sim-CSRF-Kind": "token_shown"})

    def _transfer(self, req: HttpRequest, defense: str) -> HttpResponse:
        """Shared handler for the vulnerable (POST /transfer) and secure
        (POST /secure-transfer) endpoints (YC-035.6) — 'defense' is the
        only difference in behavior: the vulnerable path trusts the
        session cookie alone; the secure path additionally validates the
        Origin header (when present) and requires a matching csrf_token.
        Neither ever touches a real financial system — 'balances' are
        training-only in-memory integers on this WebApp instance."""
        username = self._session_user(req)
        if not username:
            return self._json_error(
                401, "Unauthorized", {"status": "error", "message": "Authentication required"},
                extra_headers={"X-Sim-CSRF-Kind": "unauthenticated"})

        data = parse_body(req.body, req.headers.get("Content-Type", ""))
        recipient = data.get("recipient") or TRANSFER_RECIPIENT
        try:
            amount = int(data.get("amount", 0))
        except ValueError:
            amount = 0

        if defense == "secure":
            # Origin validation (conceptual defense, YC-035.6): only
            # enforced when the header is actually present — a real
            # browser doesn't always send Origin, so this never blocks a
            # request that simply omits it, only one that explicitly
            # carries an unexpected value. Checked before the token so a
            # forged-origin request is rejected regardless of whether a
            # token was also attached.
            origin = req.headers.get("Origin")
            if origin is not None and origin != TRUSTED_ORIGIN:
                return self._json_error(
                    403, "Forbidden",
                    {"status": "error", "message": "CSRF validation failed: unexpected Origin."},
                    extra_headers={"X-Sim-CSRF-Kind": "origin_rejected"})
            sid = req.cookies.get("session_id", "")
            expected_token = _csrf_token_for_session(sid)
            submitted_token = data.get("csrf_token")
            if not submitted_token:
                return self._json_error(
                    403, "Forbidden",
                    {"status": "error", "message": "CSRF validation failed: missing csrf_token."},
                    extra_headers={"X-Sim-CSRF-Kind": "missing_token"})
            if submitted_token != expected_token:
                return self._json_error(
                    403, "Forbidden",
                    {"status": "error", "message": "CSRF validation failed: invalid csrf_token."},
                    extra_headers={"X-Sim-CSRF-Kind": "invalid_token"})

        sender_balance = self._balance(username)
        if amount <= 0 or amount > sender_balance:
            return self._json_error(
                400, "Bad Request", {"status": "error", "message": "Invalid transfer amount."},
                extra_headers={"X-Sim-CSRF-Kind": "invalid_amount"})

        self.balances[username] = sender_balance - amount
        self.balances[recipient] = self._balance(recipient) + amount
        transfer = Transfer(id=len(self.transfers) + 1, sender=username, recipient=recipient,
                            amount=amount, defense=defense,
                            created_at=f"training-transfer-{len(self.transfers) + 1}")
        self.transfers.append(transfer)

        if defense == "vulnerable":
            # 'attack_simulated' marks a forged-Origin request that still
            # succeeded — the actual vulnerability this mission
            # demonstrates. A plain, same-origin test transfer (no
            # attacker Origin header) is just 'vulnerable_success'.
            kind = ("attack_simulated" if req.headers.get("Origin") == ATTACKER_ORIGIN
                   else "vulnerable_success")
        else:
            kind = "token_valid"
        return self._json_ok(
            {"status": "success", "sender": username, "recipient": recipient,
             "amount": amount, "balance": self.balances[username]},
            extra_headers={"X-Sim-CSRF-Kind": kind})

    def _transfer_history(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if not username:
            return self._redirect("/login")
        mine = [t for t in self.transfers if t.sender == username]
        lines = ["Transfer history:"]
        if not mine:
            lines.append("  (no transfers yet)")
        for t in mine:
            lines.append(f"  #{t.id} {t.sender} -> {t.recipient}: {t.amount} ({t.defense})")
        return self._ok("\n".join(lines), content_type="text/plain")

    def _upload_get(self, req: HttpRequest) -> HttpResponse:
        """Informational upload page (YC-035.7) — describes the
        vulnerable pipeline's single check (file extension only) and
        lists the fixed training files a student can select. Visiting it
        never itself uploads anything."""
        body = (
            "Upload Avatar — Vulnerable\n\n"
            "POST /upload accepts an image if its filename extension is one of: "
            + ", ".join(sorted(VULNERABLE_UPLOAD_EXTENSIONS)) + ".\n"
            "It does not check the declared Content-Type, does not inspect the "
            "actual file content/signature, and stores the file under its "
            "original, web-accessible filename.\n\n"
            "Training files: " + ", ".join(sorted(TRAINING_FILES)) + ".\n"
            "Compare with the protected version at /secure-upload."
        )
        return self._ok(body, content_type="text/plain")

    def _secure_upload_get(self, req: HttpRequest) -> HttpResponse:
        """Informational secure-upload page (YC-035.7) — describes the
        full validation pipeline. Visiting it never itself uploads
        anything."""
        body = (
            "Upload Avatar — Secure\n\n"
            "POST /secure-upload additionally validates: file size (max "
            f"{UPLOAD_SIZE_LIMIT_BYTES // 1_000_000} MB), a stricter extension "
            "allowlist (" + ", ".join(sorted(SECURE_UPLOAD_EXTENSIONS)) + ", no "
            ".svg), filename normalization (rejects path-traversal-shaped "
            "names), the declared Content-Type against the extension, and the "
            "detected content signature against the extension — rejecting "
            "executable content outright. Accepted files are stored under a "
            "randomized, non-web-accessible name."
        )
        return self._ok(body, content_type="text/plain")

    def _upload_security_page(self, req: HttpRequest) -> HttpResponse:
        """The Upload Security Pipeline overview (YC-035.7 §27) — a fixed,
        numbered description of every independent control a secure
        upload pipeline applies, used by the mission's Vulnerable-vs-
        Secure panel and final-investigation hints."""
        body = (
            "FILE UPLOAD SECURITY PIPELINE\n"
            "1. Authentication\n"
            "2. Authorization\n"
            "3. Size validation\n"
            "4. Extension allowlist\n"
            "5. MIME validation\n"
            "6. Content/signature validation\n"
            "7. Filename normalization\n"
            "8. Randomized storage name\n"
            "9. Safe (non-web-accessible) storage\n"
            "10. Controlled serving\n\n"
            "No single layer is sufficient by itself — defense in depth means "
            "applying multiple independent controls, since any one of them "
            "could be misconfigured or bypassed."
        )
        return self._ok(body, content_type="text/plain")

    def _upload_post(self, req: HttpRequest, pipeline: str) -> HttpResponse:
        """Shared handler for the vulnerable (POST /upload) and secure
        (POST /secure-upload) endpoints (YC-035.7). There is no real
        file content anywhere: 'filename', 'content_type', 'size', and
        'signature' are explicit, client-supplied form fields — the
        simulated stand-ins for a real client's filename, declared
        Content-Type, byte size, and detected magic bytes. Nothing here
        ever reads, writes, or executes a real file."""
        username = self._session_user(req)
        if not username:
            return self._json_error(
                401, "Unauthorized", {"status": "error", "message": "Authentication required"},
                extra_headers={"X-Sim-Upload-Kind": "unauthenticated"})

        data = parse_body(req.body, req.headers.get("Content-Type", ""))
        filename = data.get("filename", "")
        content_type = data.get("content_type", "")
        try:
            size = int(data.get("size", 0))
        except ValueError:
            size = 0
        signature = data.get("signature", "").upper()
        extension = _extension_of(filename)
        base_headers = {
            "X-Sim-Upload-Extension": extension, "X-Sim-Upload-Mime": content_type,
            "X-Sim-Upload-Signature": signature,
        }

        if size > UPLOAD_SIZE_LIMIT_BYTES:
            return self._json_error(
                413, "Payload Too Large", {"status": "error", "message": "File exceeds the training size limit."},
                extra_headers={**base_headers, "X-Sim-Upload-Kind": "size_exceeded"})

        allowed_extensions = (VULNERABLE_UPLOAD_EXTENSIONS if pipeline == "vulnerable"
                             else SECURE_UPLOAD_EXTENSIONS)
        if extension not in allowed_extensions:
            return self._json_error(
                415, "Unsupported Media Type", {"status": "error", "message": "File extension not allowed."},
                extra_headers={**base_headers, "X-Sim-Upload-Kind": "extension_rejected"})

        if pipeline == "secure":
            if _looks_like_path_traversal(filename):
                resolved = f"/private-training-storage/{filename.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1]}"
                return self._json_error(
                    403, "Forbidden",
                    {"status": "error", "message": "Path traversal blocked.",
                     "requested_path": filename, "resolved_training_path": resolved},
                    extra_headers={**base_headers, "X-Sim-Upload-Kind": "path_traversal_blocked"})

            expected_mime = EXPECTED_MIME_FOR_EXTENSION.get(extension)
            if content_type != expected_mime:
                return self._json_error(
                    415, "Unsupported Media Type",
                    {"status": "error", "message": "Declared Content-Type does not match the extension."},
                    extra_headers={**base_headers, "X-Sim-Upload-Kind": "mime_rejected"})

            if signature == "EXECUTABLE":
                return self._json_error(
                    403, "Forbidden", {"status": "error", "message": "Executable content detected. Blocked."},
                    extra_headers={**base_headers, "X-Sim-Upload-Kind": "executable_blocked"})

            expected_signature = EXPECTED_SIGNATURE_FOR_EXTENSION.get(extension)
            if signature != expected_signature:
                return self._json_error(
                    415, "Unsupported Media Type",
                    {"status": "error", "message": "Content does not match declared file type."},
                    extra_headers={**base_headers, "X-Sim-Upload-Kind": "signature_rejected"})

            stored_name = self._random_stored_name(extension)
            uploaded = UploadedFile(
                id=stored_name, owner=username, original_filename=filename, stored_name=stored_name,
                extension=extension, mime=content_type, signature=signature,
                size=size, category=_category_for_signature(signature), pipeline="secure",
                web_accessible=False, created_at=f"training-upload-{len(self.uploads) + 1}")
            self.uploads.append(uploaded)
            return self._json_ok(
                {"status": "success", "id": stored_name, "stored_name": stored_name, "web_accessible": False},
                extra_headers={**base_headers, "X-Sim-Upload-Kind": "accepted_secure",
                              "X-Sim-Upload-Stored-Name": stored_name, "X-Sim-Upload-Web-Accessible": "false"})

        # Vulnerable pipeline — extension already checked above; nothing
        # else is validated, so a content/signature mismatch (or a
        # disguised-executable training file) is stored exactly like any
        # other accepted upload, under its original, web-accessible name.
        expected_signature = EXPECTED_SIGNATURE_FOR_EXTENSION.get(extension)
        mismatch = bool(signature) and signature != expected_signature
        uploaded = UploadedFile(
            id=filename, owner=username, original_filename=filename, stored_name=filename,
            extension=extension, mime=content_type, signature=signature,
            size=size, category=_category_for_signature(signature), pipeline="vulnerable",
            web_accessible=True, created_at=f"training-upload-{len(self.uploads) + 1}")
        self.uploads.append(uploaded)
        if signature == "EXECUTABLE":
            kind = "executable_accepted"
        elif mismatch:
            kind = "content_mismatch"
        else:
            kind = "accepted_vulnerable"
        return self._json_ok(
            {"status": "success", "id": filename, "stored_name": filename, "web_accessible": True},
            extra_headers={**base_headers, "X-Sim-Upload-Kind": kind,
                          "X-Sim-Upload-Stored-Name": filename, "X-Sim-Upload-Web-Accessible": "true"})

    def _uploads_list(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if not username:
            return self._redirect("/login")
        mine = [u for u in self.uploads if u.owner == username]
        lines = ["Uploaded files:"]
        if not mine:
            lines.append("  (no uploads yet)")
        for u in mine:
            access = "web-accessible" if u.web_accessible else "private"
            lines.append(f"  #{u.id} {u.stored_name} ({u.pipeline}, {access})")
        return self._ok("\n".join(lines), content_type="text/plain")

    def _upload_detail(self, req: HttpRequest, upload_id: str) -> HttpResponse:
        """The 'controlled download handler' (YC-035.7 §19) — serves an
        upload's metadata only by its opaque id, never by resolving a
        client-supplied filesystem path. Auth-gated, same as every other
        protected page."""
        username = self._session_user(req)
        if not username:
            return self._redirect("/login")
        match = next((u for u in self.uploads if u.id == upload_id and u.owner == username), None)
        if match is None:
            return self._not_found()
        access = "web-accessible" if match.web_accessible else "private (served via this controlled handler)"
        body = (f"Upload #{match.id}\nOriginal filename: {match.original_filename}\n"
               f"Stored as: {match.stored_name}\nPipeline: {match.pipeline}\nAccess: {access}")
        return self._ok(body, content_type="text/plain")

    def _dashboard(self, req: HttpRequest) -> HttpResponse:
        username = self._session_user(req)
        if username:
            return self._ok(f"Dashboard: welcome back, {username}.")
        return self._redirect("/login")

    def _admin(self, req: HttpRequest) -> HttpResponse:
        """Authentication vs. authorization (YC-035.3): an unauthenticated
        request is 401 ("who are you?"), but the training user "student",
        while fully authenticated, is still not "admin" — 403 ("you are
        known, but not allowed here"). Only "admin" (a fictional training
        account) may pass."""
        username = self._session_user(req)
        if username is None:
            return self._error(401, "Unauthorized", "You must log in to view this page.")
        if username != "admin":
            return self._json_error(
                403, "Forbidden",
                {"error": "Forbidden",
                 "message": "You are authenticated, but not authorized to access this resource."})
        return self._ok("Admin dashboard: training-site controls.")

    def _logout(self, req: HttpRequest) -> HttpResponse:
        """Invalidates the server-side session (YC-035.0) and, as of
        YC-035.3, tells the browser to delete the cookie too
        (`deleted_cookies`) — GET keeps its original Location ("/") for
        backward compatibility with earlier missions; POST (the form-submit
        flow this mission teaches) redirects to /login instead."""
        sid = req.cookies.get("session_id")
        if sid:
            self.sessions.pop(sid, None)
        location = "/login" if req.method == "POST" else "/"
        resp = self._redirect(location)
        resp.deleted_cookies.append("session_id")
        return resp

    def expire_session(self, sid: str) -> bool:
        """Simulator-controlled session expiration (YC-035.3) — deterministic
        and explicitly triggered (the 'expire' terminal command), never tied
        to real wall-clock time. Server-side this is identical to logout
        (the session stops being recognized), but nothing tells the
        browser to drop its cookie: the whole point is that the student's
        browser *still has* the stale session_id, yet the server now
        rejects it — visibly different from logout's explicit cookie
        deletion."""
        return self.sessions.pop(sid, None) is not None

    def _session_user(self, req: HttpRequest) -> str | None:
        """Cookie-based session lookup — the browser/HTML auth mechanism."""
        sid = req.cookies.get("session_id")
        return self.sessions.get(sid) if sid else None

    def _bearer_user(self, req: HttpRequest) -> str | None:
        """Authorization: Bearer <token> lookup — a deliberately separate,
        token-based mechanism (YC-035.1) so students see cookie-session
        auth and header-token auth as two distinct concepts, not the same
        thing wearing different clothes. Only the fixed training token
        maps to an identity; nothing here is a real auth system."""
        auth = req.headers.get("Authorization", "")
        if auth == f"Bearer {API_TOKEN}":
            return "student"
        return None

    def _api_login(self, req: HttpRequest) -> HttpResponse:
        username = self._check_credentials(req)
        if username:
            return self._json_ok({"status": "success", "message": "Authentication successful"})
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Invalid credentials"})

    def _get_profile(self, username: str) -> dict[str, Any]:
        return self.profiles.setdefault(username, {"display_name": username})

    def _api_profile(self, req: HttpRequest) -> HttpResponse:
        """JSON counterpart to /profile — cookie-session protected, like
        the HTML page, to teach that a JSON API can sit behind the same
        session cookie (distinct from the bearer-token /api/me below).

        POST actually persists (YC-035.2), but only under the exact key
        'display_name' — a case-mismatched key (e.g. 'Display_Name') is
        silently ignored, matching real-world APIs that don't warn about
        unrecognized fields. Still returns 200 either way, so the bug is
        only visible by checking the field actually changed, not the
        status code — the crux of the mission's final investigation."""
        username = self._session_user(req)
        if not username:
            return self._json_error(401, "Unauthorized",
                                    {"status": "error", "message": "Authentication required"})
        profile = self._get_profile(username)
        if req.method == "POST":
            data = parse_body(req.body, req.headers.get("Content-Type", ""))
            if "display_name" in data:
                profile["display_name"] = data["display_name"]
            return self._json_ok({"status": "updated", "display_name": profile["display_name"]})
        return self._json_ok({"username": username, "display_name": profile["display_name"]})

    def _api_me(self, req: HttpRequest) -> HttpResponse:
        username = self._bearer_user(req)
        if username:
            return self._json_ok({"username": username})
        return self._json_error(401, "Unauthorized",
                                {"status": "error", "message": "Authentication required"})

    def _ok(self, body: str, content_type: str = "text/html",
           extra_headers: dict[str, str] | None = None) -> HttpResponse:
        headers = {"Content-Type": content_type, "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store"}
        if extra_headers:
            headers.update(extra_headers)
        return HttpResponse(status_code=200, reason="OK", body=body, content_type=content_type,
                            headers=headers)

    def _json_ok(self, data: dict[str, Any],
                extra_headers: dict[str, str] | None = None) -> HttpResponse:
        body = json.dumps(data)
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER, "Cache-Control": "no-store"}
        if extra_headers:
            headers.update(extra_headers)
        return HttpResponse(status_code=200, reason="OK", body=body,
                            content_type="application/json", headers=headers)

    def _json_error(self, code: int, reason: str, data: dict[str, Any],
                    extra_headers: dict[str, str] | None = None) -> HttpResponse:
        body = json.dumps(data)
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body)),
                  "Server": SERVER_HEADER}
        if extra_headers:
            headers.update(extra_headers)
        return HttpResponse(status_code=code, reason=reason, body=body,
                            content_type="application/json", headers=headers)

    def _redirect(self, location: str) -> HttpResponse:
        return HttpResponse(status_code=302, reason="Found", content_type="text/plain",
                            headers={"Location": location, "Content-Length": "0",
                                    "Server": SERVER_HEADER})

    def _error(self, code: int, reason: str, message: str) -> HttpResponse:
        return HttpResponse(status_code=code, reason=reason, body=message, content_type="text/plain",
                            headers={"Content-Type": "text/plain", "Content-Length": str(len(message)),
                                    "Server": SERVER_HEADER})

    def _not_found(self) -> HttpResponse:
        return self._error(404, "Not Found", "The requested resource was not found.")


def build_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the final objective: a
    fictional user ("Alex") visits the login page but never actually
    submits the form, so no session is ever created and /profile
    correctly denies them. Built once against an isolated WebApp
    instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/login")
    req = build_request("GET", url, timestamp=1.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("GET", url, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, timestamp=3.0)  # no cookies — never logged in
    log.append((req, app.handle(req)))

    return log


def build_content_type_bug_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the HTTP Deep Dive final
    objective (YC-035.1): a user logs in *successfully* — form submitted,
    redirect followed, session cookie set and used — but their profile
    "loads incorrectly". The root cause is a benign misconfiguration, not
    an attack: the final response's Content-Type is wrong
    (application/json instead of text/html), even though the body and
    status code are otherwise correct. Built once against an isolated
    WebApp instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/login")
    req = build_request("GET", url, timestamp=1.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("GET", url, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=3.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    resp = app.handle(req)
    # The deliberate bug: right body, right status, wrong Content-Type —
    # the actual thing the student must notice and report.
    resp.headers["Content-Type"] = "application/json"
    resp.content_type = "application/json"
    log.append((req, resp))

    return log


def build_profile_mismatch_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the Burp Fundamentals final
    objective (YC-035.2): a user ("student") logs in, then tries to update
    their display name, but a client bug sends the field under the wrong
    key ('Display_Name' instead of 'display_name'). The server accepts
    the request (200 OK) but silently ignores the unrecognized field, so
    a follow-up GET still shows the old name — "profile information not
    displaying correctly", the fictional bug report. A benign HTTP
    parameter mismatch, not an attack. Built once against an isolated
    WebApp instance — never touches the student's own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("POST", url, body='{"Display_Name": "Alex Rivera"}',
                        cookies={"session_id": sid},
                        extra_headers={"Content-Type": "application/json"}, timestamp=3.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/api/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    log.append((req, app.handle(req)))

    return log


def build_auth_lifecycle_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the Authentication & Sessions
    final objective (YC-035.3): a student reports "I logged in fine, but
    after I logged out I can't get back into my profile" — as if that were
    a bug. It isn't: the transcript shows a completely correct lifecycle —
    successful login, an authenticated /profile hit, an explicit logout
    (which deletes the session cookie server-side), then a final /profile
    request that is correctly denied because the session no longer exists.
    The "investigation" is realizing logout is supposed to do that. Built
    once against an isolated WebApp instance — never touches the student's
    own session state."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/logout")
    req = build_request("POST", url, cookies={"session_id": sid}, timestamp=3.0)
    log.append((req, app.handle(req)))

    # The browser's cookie jar would have discarded session_id after the
    # deletion above; this final request models what happens if it's sent
    # anyway (e.g. a stale tab) — still correctly rejected, since the
    # server-side session is gone either way.
    url = parse_url(f"https://{HOST}/profile")
    req = build_request("GET", url, cookies={"session_id": sid}, timestamp=4.0)
    log.append((req, app.handle(req)))

    return log


def build_sqli_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the SQL Injection
    Fundamentals final objective (YC-035.4): a report says the training
    site's search "sometimes returns every product, and sometimes
    returns none, for no obvious reason." The transcript shows a normal
    search, then the two fixed boolean training conditions against the
    vulnerable /search (all rows, then zero rows — the actual cause: an
    unsafe, string-concatenated query whose logic the input can flip),
    then the same TRUE condition against /secure-search, which returns
    the same (correct, unaffected) result as any other non-matching
    literal search term. Built once against an isolated WebApp instance
    — never touches the student's own session state, and never executes
    the injected text as SQL."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    def _req(method: str, path: str, q: str, timestamp: float) -> HttpRequest:
        url = parse_url(f"https://{HOST}{path}")
        url.query = {"q": q}
        return build_request(method, url, timestamp=timestamp)

    req = _req("GET", "/search", "laptop", 1.0)
    log.append((req, app.handle(req)))

    req = _req("GET", "/search", TRAINING_TRUE_PAYLOAD, 2.0)
    log.append((req, app.handle(req)))

    req = _req("GET", "/search", TRAINING_FALSE_PAYLOAD, 3.0)
    log.append((req, app.handle(req)))

    req = _req("GET", "/secure-search", TRAINING_TRUE_PAYLOAD, 4.0)
    log.append((req, app.handle(req)))

    return log


def build_xss_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the XSS Fundamentals final
    objective (YC-035.5): a bug report says "our search bar and comments
    section might be exposing us to script injection." The five-request
    transcript shows a normal search (no marker), the same search with
    the fixed training marker (reflected, immediately visible), a
    feedback submission carrying the marker (stored, not yet visible),
    viewing /comments (the delayed, stored reflection — the actual
    moment the simulated event fires), and the same training marker
    against /secure-search (HTML-escaped, no event) — reflected vs.
    stored vs. defended, side by side. Built once against an isolated
    WebApp instance — never touches the student's own session state, and
    never executes anything as real JavaScript."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    def _get(path: str, q: dict[str, str], timestamp: float) -> HttpRequest:
        url = parse_url(f"https://{HOST}{path}")
        url.query = dict(q)
        return build_request("GET", url, timestamp=timestamp)

    req = _get("/search", {"q": "laptop"}, 1.0)
    log.append((req, app.handle(req)))

    marker = TRAINING_XSS_MARKERS[0]
    req = _get("/search", {"q": marker}, 2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/feedback")
    req = build_request("POST", url, body=f"name=student&comment={marker}", timestamp=3.0)
    log.append((req, app.handle(req)))

    req = _get("/comments", {}, 4.0)
    log.append((req, app.handle(req)))

    req = _get("/secure-search", {"q": marker}, 5.0)
    log.append((req, app.handle(req)))

    return log


def build_csrf_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the CSRF Fundamentals final
    objective (YC-035.6): a bug report says "a training user's balance
    changed after they visited an unrelated page — they never clicked
    transfer." The five-request transcript shows a normal login, a
    legitimate transfer, a forged-looking transfer (attacker Origin/
    Referer headers, but the browser's own session cookie) succeeding
    against the vulnerable endpoint — the actual cause — then the same
    forged shape sent to the secure endpoint without a token (rejected)
    and again with the correct token (accepted), proving the anti-CSRF
    token is the fix. Built once against an isolated WebApp instance —
    never touches the student's own session state, and never makes a
    real cross-origin request (Origin/Referer here are just request
    header values, exactly like any other header this module handles)."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    url = parse_url(f"https://{HOST}/transfer")
    req = build_request("POST", url, body="recipient=training-user&amount=50",
                        cookies={"session_id": sid}, timestamp=2.0)
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/transfer")
    req = build_request("POST", url, body="recipient=training-user&amount=100",
                        cookies={"session_id": sid}, timestamp=3.0,
                        extra_headers={"Origin": ATTACKER_ORIGIN, "Referer": f"{ATTACKER_ORIGIN}/"})
    log.append((req, app.handle(req)))

    url = parse_url(f"https://{HOST}/secure-transfer")
    req = build_request("POST", url, body="recipient=training-user&amount=100",
                        cookies={"session_id": sid}, timestamp=4.0,
                        extra_headers={"Origin": ATTACKER_ORIGIN, "Referer": f"{ATTACKER_ORIGIN}/"})
    log.append((req, app.handle(req)))

    token = _csrf_token_for_session(sid)
    url = parse_url(f"https://{HOST}/secure-transfer")
    req = build_request("POST", url, body=f"recipient=training-user&amount=100&csrf_token={token}",
                        cookies={"session_id": sid}, timestamp=5.0)
    log.append((req, app.handle(req)))

    return log


def build_upload_investigation_log() -> list[tuple[HttpRequest, HttpResponse]]:
    """A fixed, deterministic transcript for the File Upload Security
    Fundamentals final objective (YC-035.7): a bug report says "someone
    uploaded a profile picture that isn't actually an image, and it's
    sitting in a public folder." The six-request transcript shows a
    login, a normal accepted upload (vulnerable, web-accessible), a
    disguised-executable file ('shell.jpg' — an image extension, but an
    EXECUTABLE content signature) accepted by the vulnerable
    extension-only pipeline, the same file rejected by the secure
    pipeline's signature check, an oversized file rejected by the shared
    size limit, and a normal upload accepted by the secure pipeline
    (randomized name, private) — showing the vulnerability and its fix
    side by side. Built once against an isolated WebApp instance — never
    touches the student's own session state, and never handles a real
    file's bytes."""
    app = WebApp()
    log: list[tuple[HttpRequest, HttpResponse]] = []

    url = parse_url(f"https://{HOST}/auth/login")
    req = build_request("POST", url, body="username=student&password=training123", timestamp=1.0)
    resp = app.handle(req)
    log.append((req, resp))
    sid = resp.cookies["session_id"]

    def _upload_req(path: str, filename: str, timestamp: float) -> HttpRequest:
        info = TRAINING_FILES[filename]
        body = (f"filename={filename}&content_type={info['mime']}"
               f"&size={info['size']}&signature={info['signature']}")
        url = parse_url(f"https://{HOST}{path}")
        return build_request("POST", url, body=body, cookies={"session_id": sid}, timestamp=timestamp)

    req = _upload_req("/upload", "avatar.jpg", 2.0)
    log.append((req, app.handle(req)))

    req = _upload_req("/upload", "shell.jpg", 3.0)
    log.append((req, app.handle(req)))

    req = _upload_req("/secure-upload", "shell.jpg", 4.0)
    log.append((req, app.handle(req)))

    req = _upload_req("/upload", "oversized.jpg", 5.0)
    log.append((req, app.handle(req)))

    req = _upload_req("/secure-upload", "avatar.jpg", 6.0)
    log.append((req, app.handle(req)))

    return log


_INVESTIGATION_BUILDERS: dict[str, Callable[[], list[tuple[HttpRequest, HttpResponse]]]] = {
    "login-flow": build_investigation_log,
    "content-type-bug": build_content_type_bug_log,
    "profile-mismatch": build_profile_mismatch_log,
    "auth-lifecycle": build_auth_lifecycle_log,
    "sqli-investigation": build_sqli_investigation_log,
    "xss-investigation": build_xss_investigation_log,
    "csrf-investigation": build_csrf_investigation_log,
    "upload-investigation": build_upload_investigation_log,
}


@dataclass
class WebSession:
    """The student's own client-side state: cookie jar + request history."""
    cookies: dict[str, str] = field(default_factory=dict)
    history: list[tuple[HttpRequest, HttpResponse]] = field(default_factory=list)

    @property
    def last_request(self) -> HttpRequest | None:
        return self.history[-1][0] if self.history else None

    @property
    def last_response(self) -> HttpResponse | None:
        return self.history[-1][1] if self.history else None

    def record(self, req: HttpRequest, resp: HttpResponse) -> None:
        self.history.append((req, resp))
        for k, v in resp.cookies.items():
            self.cookies[k] = v
        # Logout's Set-Cookie deletion (YC-035.3) — the browser drops the
        # cookie from its own jar exactly as it would apply any other
        # Set-Cookie instruction from the server.
        for k in resp.deleted_cookies:
            self.cookies.pop(k, None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cookies": self.cookies,
            "history": [[dataclasses.asdict(r), dataclasses.asdict(s)]
                       for r, s in self.history[-20:]],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WebSession:
        ws = cls()
        ws.cookies = d.get("cookies", {})
        ws.history = [(HttpRequest(**r), HttpResponse(**s)) for r, s in d.get("history", [])]
        return ws


@dataclass
class ProxyState:
    """Intercepting-proxy state for a WebLab session (YC-035.2) — mirrors
    WebSession's shape: small, explicit, mutable, in-memory only. Every
    counter here backs a structured validator check (mission_validator.py)
    instead of matching rendered text, per the project's established
    'do not validate by brittle string matching' discipline."""
    intercept_enabled: bool = False
    pending: HttpRequest | None = None
    intercepted_count: int = 0
    forwarded_count: int = 0
    dropped_count: int = 0
    blocked_count: int = 0
    repeater_request: HttpRequest | None = None
    repeater_loaded_count: int = 0
    repeater_sent_count: int = 0
    compared_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "intercept_enabled": self.intercept_enabled,
            "pending": dataclasses.asdict(self.pending) if self.pending else None,
            "intercepted_count": self.intercepted_count,
            "forwarded_count": self.forwarded_count,
            "dropped_count": self.dropped_count,
            "blocked_count": self.blocked_count,
            "repeater_request": dataclasses.asdict(self.repeater_request)
                if self.repeater_request else None,
            "repeater_loaded_count": self.repeater_loaded_count,
            "repeater_sent_count": self.repeater_sent_count,
            "compared_count": self.compared_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProxyState:
        ps = cls()
        ps.intercept_enabled = d.get("intercept_enabled", False)
        ps.pending = HttpRequest(**d["pending"]) if d.get("pending") else None
        ps.intercepted_count = d.get("intercepted_count", 0)
        ps.forwarded_count = d.get("forwarded_count", 0)
        ps.dropped_count = d.get("dropped_count", 0)
        ps.blocked_count = d.get("blocked_count", 0)
        ps.repeater_request = HttpRequest(**d["repeater_request"]) if d.get("repeater_request") else None
        ps.repeater_loaded_count = d.get("repeater_loaded_count", 0)
        ps.repeater_sent_count = d.get("repeater_sent_count", 0)
        ps.compared_count = d.get("compared_count", 0)
        return ps


@dataclass
class SqliLabState:
    """SQL Injection Fundamentals training state (YC-035.4) — mirrors
    ProxyState: small, explicit, mutable, in-memory only. Every field
    backs a structured validator check instead of matching rendered
    text; set from the response's 'X-Sim-Query-Kind' header (see
    commands.py's _track_sqli_response), never by re-parsing raw text."""
    query_inspections: int = 0
    boolean_true_seen: bool = False
    boolean_false_seen: bool = False
    secure_search_tested: bool = False
    secure_login_tested: bool = False
    auth_bypass_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SqliLabState:
        return cls(
            query_inspections=d.get("query_inspections", 0),
            boolean_true_seen=d.get("boolean_true_seen", False),
            boolean_false_seen=d.get("boolean_false_seen", False),
            secure_search_tested=d.get("secure_search_tested", False),
            secure_login_tested=d.get("secure_login_tested", False),
            auth_bypass_triggered=d.get("auth_bypass_triggered", False),
        )


@dataclass
class XssLabState:
    """XSS Fundamentals training state (YC-035.5) — mirrors SqliLabState:
    small, explicit, mutable, in-memory only. Every field backs a
    structured validator check instead of matching rendered text; set
    from a response's 'X-Sim-XSS-Kind' header (see commands.py's
    _track_xss_response), never by re-parsing raw text."""
    reflected_seen: bool = False
    stored_seen: bool = False
    dom_seen: bool = False
    secure_search_tested: bool = False
    secure_feedback_tested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> XssLabState:
        return cls(
            reflected_seen=d.get("reflected_seen", False),
            stored_seen=d.get("stored_seen", False),
            dom_seen=d.get("dom_seen", False),
            secure_search_tested=d.get("secure_search_tested", False),
            secure_feedback_tested=d.get("secure_feedback_tested", False),
        )


@dataclass
class CsrfLabState:
    """Cross-Site Request Forgery Fundamentals training state (YC-035.6)
    — mirrors XssLabState: small, explicit, mutable, in-memory only.
    Every field backs a structured validator check instead of matching
    rendered text; set from a response's 'X-Sim-CSRF-Kind' header (see
    commands.py's _track_csrf_response) or an explicit counter
    (samesite_inspected), never by re-parsing raw text."""
    attack_simulated: bool = False
    token_viewed: bool = False
    missing_token_rejected: bool = False
    invalid_token_rejected: bool = False
    valid_token_accepted: bool = False
    origin_rejected: bool = False
    samesite_inspected: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CsrfLabState:
        return cls(
            attack_simulated=d.get("attack_simulated", False),
            token_viewed=d.get("token_viewed", False),
            missing_token_rejected=d.get("missing_token_rejected", False),
            invalid_token_rejected=d.get("invalid_token_rejected", False),
            valid_token_accepted=d.get("valid_token_accepted", False),
            origin_rejected=d.get("origin_rejected", False),
            samesite_inspected=d.get("samesite_inspected", 0),
        )


@dataclass
class UploadLabState:
    """File Upload Security Fundamentals training state (YC-035.7) —
    mirrors CsrfLabState: small, explicit, mutable, in-memory only.
    Every field backs a structured validator check instead of matching
    rendered text; set from a response's 'X-Sim-Upload-Kind'/'X-Sim-
    Upload-Signature' headers (see commands.py's _track_upload_response),
    never by re-parsing raw text."""
    signature_inspected: bool = False
    content_mismatch_seen: bool = False
    secure_rejection_seen: bool = False
    size_limit_seen: bool = False
    path_traversal_blocked: bool = False
    executable_blocked: bool = False
    vulnerable_accepted_seen: bool = False
    secure_accepted_seen: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UploadLabState:
        return cls(
            signature_inspected=d.get("signature_inspected", False),
            content_mismatch_seen=d.get("content_mismatch_seen", False),
            secure_rejection_seen=d.get("secure_rejection_seen", False),
            size_limit_seen=d.get("size_limit_seen", False),
            path_traversal_blocked=d.get("path_traversal_blocked", False),
            executable_blocked=d.get("executable_blocked", False),
            vulnerable_accepted_seen=d.get("vulnerable_accepted_seen", False),
            secure_accepted_seen=d.get("secure_accepted_seen", False),
        )


class WebLab:
    """Everything a web-fundamentals mission session needs: the
    simulated site, the student's own session, the fixed investigation
    transcript for the final objective, and (YC-035.2) intercepting-proxy
    state. `proxy` costs nothing for missions that never touch it (its
    counters simply stay at their defaults) so YC-035.0/YC-035.1 are
    unaffected. Same for `sqli` (YC-035.4) and `xss` (YC-035.5)."""

    def __init__(self, app: WebApp, investigation_log: list[tuple[HttpRequest, HttpResponse]]) -> None:
        self.app = app
        self.session = WebSession()
        self.investigation_log = investigation_log
        self.proxy = ProxyState()
        # Counts uses of the 'expire' command (YC-035.3) — deliberately a
        # simple counter, mirroring ProxyState's counters, rather than a
        # new dataclass for a single field. Distinguishes "this session
        # became invalid because the student explicitly expired it" from
        # "because they logged out", for the session_expired validator
        # check.
        self.expired_count = 0
        self.sqli = SqliLabState()
        self.xss = XssLabState()
        self.csrf = CsrfLabState()
        self.upload = UploadLabState()

    def to_dict(self) -> dict[str, Any]:
        return {"sessions": dict(self.app.sessions), "profiles": dict(self.app.profiles),
                "comments": [dataclasses.asdict(c) for c in self.app.comments],
                "balances": dict(self.app.balances),
                "transfers": [dataclasses.asdict(t) for t in self.app.transfers],
                "uploads": [dataclasses.asdict(u) for u in self.app.uploads],
                "session": self.session.to_dict(), "proxy": self.proxy.to_dict(),
                "expired_count": self.expired_count, "sqli": self.sqli.to_dict(),
                "xss": self.xss.to_dict(), "csrf": self.csrf.to_dict(),
                "upload": self.upload.to_dict()}

    def apply_state(self, snapshot: dict[str, Any]) -> None:
        self.app.sessions = dict(snapshot.get("sessions", {}))
        self.app.profiles = dict(snapshot.get("profiles", {}))
        self.app.comments = [Comment(**c) for c in snapshot.get("comments", [])]
        self.app.balances = dict(snapshot.get("balances", {}))
        self.app.transfers = [Transfer(**t) for t in snapshot.get("transfers", [])]
        self.app.uploads = [UploadedFile(**u) for u in snapshot.get("uploads", [])]
        self.session = WebSession.from_dict(snapshot.get("session", {}))
        self.proxy = ProxyState.from_dict(snapshot.get("proxy", {}))
        self.expired_count = snapshot.get("expired_count", 0)
        self.sqli = SqliLabState.from_dict(snapshot.get("sqli", {}))
        self.xss = XssLabState.from_dict(snapshot.get("xss", {}))
        self.csrf = CsrfLabState.from_dict(snapshot.get("csrf", {}))
        self.upload = UploadLabState.from_dict(snapshot.get("upload", {}))


def build_web_lab(scenario: str = "login-flow") -> WebLab:
    """`scenario` selects which fixed investigation transcript this
    mission's final objective gets (YC-035.1 needs a different one than
    YC-035.0), the same registry pattern as packets.py's CAPTURE_REGISTRY."""
    builder = _INVESTIGATION_BUILDERS.get(scenario, build_investigation_log)
    return WebLab(app=WebApp(), investigation_log=builder())


# ── Rendering — text formatting only ──
def render_request(req: HttpRequest) -> str:
    target = req.path
    if req.query:
        target += "?" + "&".join(f"{k}={v}" for k, v in req.query.items())
    lines = [f"{req.method} {target} HTTP/1.1"]
    for k, v in req.headers.items():
        lines.append(f"{k}: {v}")
    if req.cookies:
        lines.append("Cookie: " + "; ".join(f"{k}={v}" for k, v in req.cookies.items()))
    if req.body:
        lines.append("")
        lines.append(req.body)
    return "\n".join(lines)


def render_response(resp: HttpResponse) -> str:
    lines = [f"HTTP/1.1 {resp.status_code} {resp.reason}"]
    for k, v in resp.headers.items():
        lines.append(f"{k}: {v}")
    for k, v in resp.cookies.items():
        lines.append(f"Set-Cookie: {k}={v}")
    for k in resp.deleted_cookies:
        lines.append(f"Set-Cookie: {k}=; Max-Age=0")
    if resp.body:
        lines.append("")
        lines.append(resp.body)
    return "\n".join(lines)


def render_exchange(req: HttpRequest, resp: HttpResponse) -> str:
    return ("━━━━━━━━ REQUEST ━━━━━━━━\n"
           + render_request(req)
           + "\n\n━━━━━━━━ RESPONSE ━━━━━━━━\n"
           + render_response(resp))
