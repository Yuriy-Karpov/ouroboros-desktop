# Ouroboros — Docker image for web UI runtime
# Usage:
#   docker build -t ouroboros-web .
#   docker run --rm -p 8765:8765 ouroboros-web

FROM python:3.10-slim

ARG PYTHON_ENV_MODE=global

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Working directory
ENV APP_HOME=/app
WORKDIR ${APP_HOME}

# Runtime environment selection
ENV UV_PROJECT_ENVIRONMENT=${APP_HOME}/.venv \
    VIRTUAL_ENV=${APP_HOME}/.venv \
    PATH="${APP_HOME}/.venv/bin:${PATH}"

# Install uv only when requested
RUN if [ "$PYTHON_ENV_MODE" = "uv" ]; then pip install --no-cache-dir uv; fi

# Copy project metadata first so uv dependency sync can be cached
COPY pyproject.toml README.md requirements.txt VERSION ./
COPY uv.lock ./
RUN printf '%s\n' "$PYTHON_ENV_MODE" > .ouroboros-python-env

# Pre-create the project venv and install only third-party deps in uv mode.
# The application source is copied afterwards and runs directly from /app.
RUN if [ "$PYTHON_ENV_MODE" = "uv" ]; then \
      uv venv --allow-existing --python python "${APP_HOME}/.venv" && \
      uv sync --frozen --active --extra browser --no-install-project; \
    fi

# Copy application
COPY . .

# Install Python dependencies
RUN if [ "$PYTHON_ENV_MODE" = "uv" ]; then \
      uv sync --frozen --active --extra browser; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi

# Default environment
ENV OUROBOROS_SERVER_HOST=0.0.0.0 \
    OUROBOROS_SERVER_PORT=8765 \
    OUROBOROS_FILE_BROWSER_DEFAULT=${APP_HOME}

EXPOSE 8765

ENTRYPOINT ["python", "server.py"]
