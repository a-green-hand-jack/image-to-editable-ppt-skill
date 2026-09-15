#!/usr/bin/env bash
# Install the public CLI and register the Codex skill for the current user.
set -euo pipefail

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
  uv tool install --force "$source_dir"
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
printf 'Installed editppt and Codex skill: %s\n' "$skill_dir"
printf '%s\n' 'Restart Codex or refresh skill discovery before using it.'
