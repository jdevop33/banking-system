# syntax=docker/dockerfile:1
#
# Single image, three roles (web / celery worker / celery beat).
# Base is python:3.10-slim: the pinned Celery 4.4.7 stack depends on vine 1.3.0,
# which imports inspect.formatargspec/getargspec — both removed in Python 3.11.
# 3.10 is the newest CPython that runs these unchanged, still-pinned dependencies.

########## builder ##########
# Pinned by digest (not just the mutable 3.10-slim tag) so every rebuild of this
# banking image resolves the exact same base. Bump the digest deliberately.
FROM python:3.10-slim@sha256:31dd4d9529d02d7436659061cb7564cd4733fc90e5e152709a942d53382ec8d0 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# celery 4.4.7 ships legacy wheel metadata ("pytz>dev") that pip >= 24.1 rejects,
# so dependencies are installed with pip pinned below 24.1. gunicorn and whitenoise
# are deployment-only additions (never touch the app's requirements.txt).
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install "pip<24.1" \
    && /opt/venv/bin/pip install -r requirements.txt gunicorn==21.2.0 whitenoise==6.6.0

########## runtime ##########
# Same digest-pinned base as the builder stage.
FROM python:3.10-slim@sha256:31dd4d9529d02d7436659061cb7564cd4733fc90e5e152709a942d53382ec8d0 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=banking_system.settings \
    STATIC_ROOT=/app/staticfiles \
    SQLITE_PATH=/data/db.sqlite3

# Non-root user, plus a writable data dir. A named volume mounted at /data inherits
# this ownership the first time it is created, so the app user can write the sqlite file.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && install -d -o app -g app /data

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN install -d -o app -g app /app/staticfiles \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Web-oriented health check (the image's primary role). The worker and beat services
# override this with their own checks in docker-compose.prod.yml.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4).status < 500 else 1)" || exit 1

# Default (web) command: apply migrations, collect static, then serve with gunicorn.
# docker-compose.prod.yml overrides `command` for the worker and beat services.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn banking_system.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -"]
