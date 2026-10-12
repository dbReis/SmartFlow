# =============================================================================
# SmartFlow API image
# Two stages: "build" installs the dependencies and the app into a virtual
# environment with uv; the final image only copies that environment, so it
# contains no build tools, no source checkout and no uv.
# =============================================================================

FROM python:3.12-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Dependencies first: this layer is reused as long as the lock file is unchanged,
# so editing the code does not reinstall every package.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then the app itself, installed as a regular (non-editable) package.
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable


FROM python:3.12-slim-bookworm

# Run as an unprivileged user, never as root.
RUN useradd --system --uid 1001 --no-create-home smartflow

COPY --from=build /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    SMARTFLOW_LOG_FORMAT=json \
    SMARTFLOW_LOG_LEVEL=INFO

USER smartflow
EXPOSE 8888

CMD ["python", "-m", "smartflow"]
