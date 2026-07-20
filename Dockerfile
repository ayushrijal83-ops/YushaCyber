# =============================================================================
# YushaCyber — production Docker image (YC-025.0)
# =============================================================================
# Multi-stage keeps the runtime layer small: build wheels in the builder,
# copy them into a slim runtime that never sees the build toolchain.
#
# Runtime user: non-root (uid 1000). Gunicorn serves the WSGI app; the
# in-image HEALTHCHECK hits /health so orchestrators know when to reroute.
# =============================================================================

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# System packages needed to compile a couple of wheels (psycopg, cryptography).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# The gunicorn + psycopg extras aren't in requirements.txt so pin them here.
RUN pip install --user -r requirements.txt gunicorn==22.0.0 psycopg2-binary==2.9.9


# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PATH=/home/app/.local/bin:$PATH

# Runtime-only libs: libpq5 for psycopg (no compiler), curl for HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

WORKDIR /app

# Bring in the pre-built wheels then the application code.
COPY --from=builder --chown=app:app /root/.local /home/app/.local
COPY --chown=app:app . /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Two workers is a sensible starting point; scale via env in orchestration.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--threads", "4", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "--timeout", "60", \
     "app:create_app()"]
