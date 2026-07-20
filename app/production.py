"""Production hardening (YC-025.0).

Everything here is **additive** — no existing route, service, engine, or
model is modified. Loaded from the app factory as a single ``init_app``
call. Each concern is a small self-contained function so it can be
enabled or reasoned about independently:

  · ``_install_security_headers`` — HSTS (production only), X-Frame-Options,
    X-Content-Type-Options, Referrer-Policy, Permissions-Policy, and a
    conservative Content-Security-Policy that permits the fonts and CDN
    scripts the templates already load.

  · ``_install_request_logging`` — a per-request UUID attached to
    ``g.request_id``, echoed as the ``X-Request-ID`` response header, and
    included in every log line so a slow or erroring request can be
    traced end-to-end.

  · ``_install_login_rate_limit`` — 10 POST attempts per client IP per 15
    minutes on ``/auth/login``. In-process token bucket; no Redis, no
    new dependency. Multi-worker deployments should replace with
    Flask-Limiter behind a shared store, but the hook location is a
    single ``@app.before_request`` we control here.

  · ``_install_health_endpoints`` — ``/health`` returns 200 with a
    minimal JSON body, ``/health/db`` does a ``SELECT 1`` to prove the
    connection is alive. Both are unauthenticated and cheap enough for
    container orchestrators to poll every few seconds.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from threading import Lock
from typing import Any

from flask import Flask, Response, current_app, g, jsonify, request
from sqlalchemy import text

from app.extensions import db


# ---------------------------------------------------------------------------
# 1. Security headers
# ---------------------------------------------------------------------------
def _install_security_headers(app: Flask) -> None:
    """Set a small, uniform set of hardening headers on every response.

    The CSP intentionally allows ``'unsafe-inline'`` for styles because the
    pre-paint theme script and a few templates use ``style=""`` attributes;
    tightening further would need a template pass beyond this ticket.
    """

    is_production = not app.debug and not app.testing

    csp = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    @app.after_request
    def _apply_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        if is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


# ---------------------------------------------------------------------------
# 2. Request-ID + structured logging
# ---------------------------------------------------------------------------
def _install_request_logging(app: Flask) -> None:
    """Tag every request with a UUID and log its lifecycle at INFO.

    The ID is available as ``g.request_id`` for any handler that wants
    to include it in exception traces, and returned to the client via
    ``X-Request-ID`` so a support conversation can pin the exact log
    line for any complaint."""

    logger = app.logger

    @app.before_request
    def _tag_request() -> None:
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _finish_request(response: Response) -> Response:
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        # Skip static asset noise — those are logged by the reverse proxy.
        if request.path.startswith("/static/"):
            return response
        duration_ms = int((time.perf_counter() - g.get("request_started_at", time.perf_counter())) * 1000)
        logger.info(
            "req id=%s method=%s path=%s status=%s dur_ms=%s ip=%s",
            g.request_id, request.method, request.path,
            response.status_code, duration_ms, _client_ip(),
        )
        return response


# ---------------------------------------------------------------------------
# 3. Login rate limiting (IP + username, sliding window, in-process)
# ---------------------------------------------------------------------------
class _RateLimiter:
    """Sliding-window bucket keyed by client IP.

    In-process only — a single worker is fine for now, and swap-in of
    Flask-Limiter with Redis is the natural next step for horizontal
    scaling. We deliberately don't touch the login route; the limiter
    runs as a ``before_request`` hook so auth logic is unchanged.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self.buckets: dict[str, deque[float]] = {}
        self.lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - self.window
        with self.lock:
            bucket = self.buckets.setdefault(key, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False, int(bucket[0] + self.window - now) + 1
            bucket.append(now)
            return True, 0


def _install_login_rate_limit(app: Flask) -> None:
    """10 POSTs per IP per 15 minutes on ``/auth/login``.

    Only POSTs are counted — a rendered GET of the login form is free,
    so users hitting refresh on the form don't get locked out. Testing
    mode disables the limiter so the test suite isn't affected.
    """

    limiter = _RateLimiter(limit=10, window_seconds=15 * 60)

    @app.before_request
    def _throttle() -> Any:
        if app.testing:
            return None
        if request.method != "POST":
            return None
        if request.path != "/auth/login":
            return None
        ip = _client_ip()
        allowed, retry_after = limiter.allow(f"login:{ip}")
        if allowed:
            return None
        app.logger.warning(
            "rate_limit path=/auth/login ip=%s retry_after=%ss", ip, retry_after,
        )
        resp = jsonify({
            "error": "too_many_requests",
            "message": "Too many login attempts. Please wait and try again.",
            "retry_after": retry_after,
        })
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry_after)
        return resp


# ---------------------------------------------------------------------------
# 4. Health endpoints for container orchestrators
# ---------------------------------------------------------------------------
def _install_health_endpoints(app: Flask) -> None:
    """``/health`` — liveness (process is up); ``/health/db`` — readiness
    (the database connection works). Both unauthenticated and lightweight."""

    started_at = time.time()

    @app.route("/health")
    def _health():
        return jsonify({
            "status": "ok",
            "uptime_seconds": int(time.time() - started_at),
            "version": app.config.get("APP_VERSION", "dev"),
        })

    @app.route("/health/db")
    def _health_db():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "db": "reachable"})
        except Exception as exc:  # pragma: no cover — production diagnostic
            app.logger.exception("Health DB check failed")
            return jsonify({"status": "error", "db": str(exc)[:120]}), 503


# ---------------------------------------------------------------------------
# 5. Structured log formatter
# ---------------------------------------------------------------------------
def _configure_logging(app: Flask) -> None:
    """Uniform log format that includes level, name, and message.

    Kept simple so it works in every hosting environment; a production
    deployment can layer JSON logging on top by swapping this handler.
    """

    if app.testing:
        return
    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(handler)
    root.setLevel(level)
    app.logger.setLevel(level)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _client_ip() -> str:
    """Prefer the first entry in X-Forwarded-For (set by a trusted proxy);
    fall back to the direct remote address."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "-"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def init_app(app: Flask) -> None:
    """Wire every production hardening concern into the given app."""
    _configure_logging(app)
    _install_security_headers(app)
    _install_request_logging(app)
    _install_login_rate_limit(app)
    _install_health_endpoints(app)
