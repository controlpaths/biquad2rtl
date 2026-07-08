#!/usr/bin/env bash
set -euo pipefail

# Registers the filter2rtl MCP server and links the add-biquad-filter skill
# into the user's Claude Code installation, so both are available from any
# project (not just while working inside this repo).
#
# Usage: ./install.sh [--scope user|project]

SCOPE="user"
if [[ "${1:-}" == "--scope" && -n "${2:-}" ]]; then
  SCOPE="$2"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
MCP_SERVER="$REPO_ROOT/mcp/mcp_server.py"
SKILL_SRC="$REPO_ROOT/.claude/skills/add-biquad-filter"
SKILL_DST="$HOME/.claude/skills/add-biquad-filter"

if ! command -v claude >/dev/null 2>&1; then
  echo "error: 'claude' CLI not found in PATH" >&2
  exit 1
fi

echo "==> Ensuring the Python virtual environment exists (make venv)"
make -C "$REPO_ROOT" venv

echo "==> Registering the filter2rtl MCP server (scope: $SCOPE)"
if claude mcp list 2>/dev/null | grep -q "^filter2rtl"; then
  echo "    filter2rtl is already registered, skipping (run 'claude mcp remove filter2rtl' first to reinstall)"
else
  claude mcp add filter2rtl --scope "$SCOPE" -- "$VENV_PYTHON" "$MCP_SERVER"
fi

echo "==> Linking the add-biquad-filter skill into ~/.claude/skills"
mkdir -p "$HOME/.claude/skills"
if [[ -L "$SKILL_DST" ]]; then
  if [[ "$(readlink "$SKILL_DST")" == "$SKILL_SRC" ]]; then
    echo "    already linked, skipping"
  else
    echo "    warning: $SKILL_DST is a symlink to a different target, leaving it untouched" >&2
  fi
elif [[ -e "$SKILL_DST" ]]; then
  echo "    warning: $SKILL_DST already exists and is not a symlink, leaving it untouched" >&2
else
  ln -s "$SKILL_SRC" "$SKILL_DST"
  echo "    linked $SKILL_DST -> $SKILL_SRC"
fi

echo "==> Done. Verify with: claude mcp list"
