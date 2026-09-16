#!/usr/bin/env bash
# Public user installer: download a release ref, install the CLI, and register
# the bundled Codex skill. For an existing checkout use .agents/scripts/install.sh.
set -euo pipefail

min_python_major=3
min_python_minor=10

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.10+ is required. Install Python before running this installer.' >&2
    exit 1
  fi
  python3 - "$min_python_major" "$min_python_minor" <<'PY'
import sys
required = (int(sys.argv[1]), int(sys.argv[2]))
if sys.version_info[:2] < required:
    print(f"Python {required[0]}.{required[1]}+ is required; found {sys.version.split()[0]}", file=sys.stderr)
    raise SystemExit(1)
PY
}

check_renderer() {
  local missing=0
  if ! command -v soffice >/dev/null 2>&1 && ! command -v libreoffice >/dev/null 2>&1; then
    printf '%s\n' 'warning: LibreOffice (soffice/libreoffice) is missing; PPTX to PDF export will be unavailable.' >&2
    missing=1
  fi
  if ! command -v pdftoppm >/dev/null 2>&1; then
    printf '%s\n' 'warning: Poppler pdftoppm is missing; PDF render validation will be unavailable.' >&2
    missing=1
  fi
  if ! command -v pdftocairo >/dev/null 2>&1; then
    printf '%s\n' 'warning: Poppler pdftocairo is missing; SVG formula conversion will fall back to PNG or another converter.' >&2
  fi
  if [ "${EDITPPT_REQUIRE_SYSTEM_DEPS:-0}" = 1 ] && [ "$missing" -ne 0 ]; then
    printf '%s\n' 'Set EDITPPT_REQUIRE_SYSTEM_DEPS=0 to install without optional system renderers.' >&2
    exit 1
  fi
}

check_python

repo="${EDITPPT_REPO:-a-green-hand-jack/image-to-editable-ppt-skill}"
ref="${EDITPPT_REF:-main}"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/image-to-editable-ppt.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

archive="$tmp/source.tar.gz"
url="https://codeload.github.com/${repo}/tar.gz/refs/heads/${ref}"
curl -fsSL "$url" -o "$archive"
tar -xzf "$archive" -C "$tmp"
source_dir="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name '*image-to-editable-ppt-skill*' -print -quit)"
test -n "$source_dir" && test -f "$source_dir/pyproject.toml"

if command -v uv >/dev/null 2>&1; then
  uv tool install --force --reinstall "$source_dir"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$source_dir"
else
  printf '%s\n' 'Install uv or pipx first: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 1
fi

skill_home="${CODEX_HOME:-$HOME/.codex}"
skill_dir="${skill_home}/../.agents/skills/image-to-editable-ppt"
mkdir -p "$(dirname "$skill_dir")"
rm -rf "$skill_dir"
cp -R "$source_dir/src/editppt/skills/image-to-editable-ppt" "$skill_dir"

command -v editppt >/dev/null 2>&1
check_renderer
printf 'Installed editppt and Codex skill: %s\n' "$skill_dir"
printf '%s\n' 'Restart Codex or refresh skill discovery before using it.'
