#!/usr/bin/env bash
# Install this checkout. Never pull, overwrite, or remove a repository.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if command -v uv >/dev/null 2>&1; then
  uv tool install --force "$repo_dir"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "$repo_dir"
else
  printf 'Install uv or pipx first. See USER.md.\n' >&2
  exit 1
fi
editppt --help >/dev/null
printf 'CLI installed. Register the skill from %s/src/editppt/skills/image-to-editable-ppt (see USER.md).\n' "$repo_dir"
