#!/usr/bin/env bash
# Installs the Python and web dependencies and builds the web app (runs once, when the
# codespace is created). The servers start when the editor attaches (devcontainer.json).
set -euo pipefail
pipx install uv==0.8.17
uv sync --frozen
corepack enable || npm install --global pnpm@10.33.0
pnpm -C web install --frozen-lockfile
pnpm -C web build
