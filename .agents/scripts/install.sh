#!/usr/bin/env bash
# Developer-only installer for this existing checkout. Never pull, overwrite,
# or remove a repository; end users should use the repository-root install.sh.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.10+ is required. Install Python before running this installer.' >&2
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info[:2] < (3, 10):
    print(f"Python 3.10+ is required; found {sys.version.split()[0]}", file=sys.stderr)
    raise SystemExit(1)
PY

if command -v uv >/dev/null 2>&1; then
  uv tool install --force --reinstall --editable "$repo_dir"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$repo_dir"
else
  printf 'Install uv or pipx first. See USER.md.\n' >&2
  exit 1
fi
editppt --help >/dev/null
if ! command -v soffice >/dev/null 2>&1 && ! command -v libreoffice >/dev/null 2>&1; then
  printf '%s\n' 'warning: LibreOffice (soffice/libreoffice) is missing; PPTX to PDF export will be unavailable.' >&2
fi
if ! command -v pdftoppm >/dev/null 2>&1; then
  printf '%s\n' 'warning: Poppler pdftoppm is missing; PDF render validation will be unavailable.' >&2
fi
if ! command -v pdftocairo >/dev/null 2>&1; then
  printf '%s\n' 'warning: Poppler pdftocairo is missing; SVG formula conversion will fall back to PNG or another converter.' >&2
fi
printf 'Developer CLI installed from editable checkout: %s\n' "$repo_dir"
printf 'The bundled skill source is %s/src/editppt/skills/image-to-editable-ppt.\n' "$repo_dir"
