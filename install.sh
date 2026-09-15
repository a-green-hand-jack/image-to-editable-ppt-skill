#!/usr/bin/env bash
# install.sh — one-command installer for image-to-editable-ppt-skill
# Usage: curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
set -euo pipefail

REPO="a-green-hand-jack/image-to-editable-ppt-skill"
BRANCH="main"
INSTALL_DIR="${IMAGE_TO_EDITABLE_PPT_DIR:-$HOME/.image-to-editable-ppt-skill}"

info()  { printf "\033[1;34m[info]\033[0m  %s\n" "$*"; }
warn()  { printf "\033[1;33m[warn]\033[0m  %s\n" "$*"; }
error() { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

# ── prerequisites ──────────────────────────────────────────────────────────
need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "'$1' is required but not found in PATH. Install it first: $2"
  fi
}

need_cmd git  "https://git-scm.com"
need_cmd python3 "https://www.python.org/downloads/"

# uv or pipx — prefer uv
if command -v uv >/dev/null 2>&1; then
  TOOL_INSTALL="uv tool install --force"
  TOOL_CMD="uv tool"
elif command -v pipx >/dev/null 2>&1; then
  TOOL_INSTALL="pipx install --force"
  TOOL_CMD="pipx"
else
  error "Neither 'uv' nor 'pipx' found. Install one:\n  uv:  curl -fsSL https://astral.sh/uv/install.sh | sh\n  pipx: pip install pipx && pipx ensurepath"
fi

# ── clone or update ────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Updating existing installation at $INSTALL_DIR ..."
  git -C "$INSTALL_DIR" pull --ff-only || {
    warn "git pull failed; re-cloning into $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    git clone --depth 1 "https://github.com/${REPO}.git" "$INSTALL_DIR"
  }
else
  info "Cloning $REPO into $INSTALL_DIR ..."
  rm -rf "$INSTALL_DIR"
  git clone --depth 1 "https://github.com/${REPO}.git" "$INSTALL_DIR"
fi

# ── install the editppt CLI ───────────────────────────────────────────────
CLI_DIR="$INSTALL_DIR/cli"
info "Installing editppt CLI via $TOOL_CMD ..."
$TOOL_INSTALL "$CLI_DIR"

# ── verify ─────────────────────────────────────────────────────────────────
info "Verifying installation ..."
if command -v editppt >/dev/null 2>&1; then
  editppt doctor || warn "'editppt doctor' reported issues — see above for details."
  printf "\n\033[1;32m✔ image-to-editable-ppt-skill installed!\033[0m\n"
  printf "  Skill root : %s\n" "$INSTALL_DIR"
  printf "  CLI        : %s\n" "$(command -v editppt)"
  printf "  Uninstall  : rm -rf %s && %s uninstall image-to-editable-ppt-cli\n\n" "$INSTALL_DIR" "$TOOL_CMD"
else
  error "editppt CLI not found after install. Check your PATH and retry."
fi
