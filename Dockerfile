# FlipScan — API, phone app, and hourly scanner in one image.
#
# Chromium is included because the Facebook collector needs a real logged-in
# browser session. That's most of the image size; build with
# `--build-arg WITH_BROWSER=false` for a ~200MB image if you're only using the
# demo or manual collectors.

FROM python:3.11-slim AS base

ARG WITH_BROWSER=true

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, so a source edit doesn't invalidate the install layer.
COPY pyproject.toml README.md ./
COPY server/flipscan/__init__.py server/flipscan/__init__.py
RUN pip install --no-cache-dir -e ".[push]"

RUN if [ "$WITH_BROWSER" = "true" ]; then \
      pip install --no-cache-dir "playwright>=1.45" && \
      playwright install --with-deps chromium && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

COPY server/ server/
COPY web/ web/

# Runs unprivileged. The data volume is chowned so SQLite and the browser
# profile stay writable.
RUN useradd --create-home --uid 10001 flipscan \
    && mkdir -p /app/data \
    && chown -R flipscan:flipscan /app
USER flipscan

VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# tini reaps the zombie processes Chromium leaves behind; without it a
# long-running scanner container slowly fills its PID table.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "flipscan.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--app-dir", "server"]
