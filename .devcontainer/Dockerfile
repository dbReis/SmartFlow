# =============================================================================
# SmartFlow dev container image
# Goal: smallest possible image with Python 3.12, uv and Claude Code.
#
# Note on comments: Docker only treats a line as a comment when "#" is the
# FIRST character of the line. That is why, inside multi-line instructions
# (lines ending in "\"), the comments sit on their own lines. Docker strips
# those lines out before running the command, so they don't break anything.
# =============================================================================
FROM python:3.12-slim-bookworm

# Multi-stage copy: grab the "uv" and "uvx" binaries straight out of Astral's
# official uv image and drop them into /bin/ of our image. Nothing else from
# that image comes along, so this is the leanest way to install uv.
# - uv  = package/project manager (replaces pip, venv, pip-tools, etc.)
# - uvx = runs a Python CLI tool in a throwaway env (like "npx" for Python)
# Tip: replace "latest" with a version (e.g. 0.x.y) for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build-time variables (only exist while the image is being built).
# Name of the non-root user we will create and work as.
ARG USERNAME=dev
# User ID. 1000 is the usual ID of the first user on Linux/WSL, so files you
# create in the mounted project folder are owned by "you" on the host too.
ARG USER_UID=1000
# Group ID; defaults to the same value as the user ID.
ARG USER_GID=$USER_UID

# Environment variables: these are baked into the image and are present in
# every shell/process inside the container.
#
# Don't write .pyc files (keeps the project folder free of __pycache__ clutter).
ENV PYTHONDONTWRITEBYTECODE=1 \
# Print output immediately instead of buffering it (logs show up right away).
    PYTHONUNBUFFERED=1 \
# Tell uv which Python to use: the one already in the base image.
    UV_PYTHON=/usr/local/bin/python \
# Forbid uv from downloading its own Python builds (would add ~100 MB).
    UV_PYTHON_DOWNLOADS=never \
# Where "uv sync" puts the project's virtual env. Default is ./.venv inside
# the project; putting it in /opt keeps the repo folder clean and avoids
# slow file access through the mounted folder.
    UV_PROJECT_ENVIRONMENT=/opt/venv \
# Copy packages from uv's cache into the venv instead of hard-linking.
# The cache and the venv can live on different filesystems, where hard
# links don't work; this silences the warning uv would otherwise print.
    UV_LINK_MODE=copy \
# Mark /opt/venv as the "active" virtual env (same as running "activate").
    VIRTUAL_ENV=/opt/venv \
# Where Claude Code keeps its login and settings. Putting everything in one
# folder lets devcontainer.json mount a volume there, so you stay logged in
# after rebuilding the container.
    CLAUDE_CONFIG_DIR=/home/${USERNAME}/.claude \
# Search order for commands. Prepending /opt/venv/bin means "python",
# "pytest", etc. resolve to the venv versions. ~/.local/bin is where the
# Claude Code installer puts the "claude" command.
    PATH=/opt/venv/bin:/home/${USERNAME}/.local/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
# Root certificates so HTTPS downloads (curl, git, uv) can be trusted.
        ca-certificates \
        curl \
        git \
# Provides "ps", "top", "kill" etc.; VS Code's server uses them to manage
# its processes inside the container.
        procps \
# "psql", to look inside the test database (psql -h db -U smartflow smartflow_test).
        postgresql-client \
# Delete the package index downloaded by "apt-get update" (~20 MB) since
# it's not needed after installing.
    && rm -rf /var/lib/apt/lists/*

# Create the user and the folders it needs. Running as a non-root user is
# safer and matches how you work on your own machine.
#
# Create a group named "dev" with the chosen group ID.
RUN groupadd --gid $USER_GID $USERNAME \
# Create user "dev": with that user ID, in that group, with a home folder
# (-m = /home/dev), and bash as its login shell (-s).
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
# Create the venv folder and the Claude config folder ("-p" = also create
# parent folders, and don't fail if they already exist).
    && mkdir -p $VIRTUAL_ENV $CLAUDE_CONFIG_DIR \
# Make "dev" the owner of both folders (-R = everything inside too), so
# uv and Claude Code can write there without root.
    && chown -R $USERNAME:$USERNAME $VIRTUAL_ENV $CLAUDE_CONFIG_DIR

# From here on, every instruction (and the container itself) runs as "dev"
# instead of root.
USER $USERNAME

# Create an empty virtual env in /opt/venv using the system Python.
# "--allow-existing" lets it reuse the folder we just created instead of
# failing because it already exists. "uv sync" will fill it later.
RUN uv venv $VIRTUAL_ENV --allow-existing

# Install Claude Code using Anthropic's native installer (a single binary,
# no Node.js needed). "curl -fsSL" downloads the script quietly and fails on
# HTTP errors; "| bash" runs it. It installs into ~/.local/bin/claude.
RUN curl -fsSL https://claude.ai/install.sh | bash
