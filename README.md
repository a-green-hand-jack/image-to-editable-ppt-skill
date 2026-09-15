# Image to Editable PPT Skill

Rebuild slide images, scanned or image-based PPT/PPTX files, and PDF decks into **object-level editable** PowerPoint (`.pptx`), preserving speaker notes when supplied.

> Use for making visual slides editable or reconstructing slides from screenshots — **not** for authoring new presentations from scratch.

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
```

This single command will:

1. **Clone** the skill repo to `~/.image-to-editable-ppt-skill` (override with `IMAGE_TO_EDITABLE_PPT_DIR`).
2. **Install** the `editppt` CLI via `uv` (preferred) or `pipx`.
3. **Verify** the installation with `editppt doctor`.

### Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| **git** | Clone the repo | [git-scm.com](https://git-scm.com) |
| **Python ≥ 3.10** | Runtime for `editppt` CLI | [python.org](https://www.python.org/downloads/) |
| **uv** or **pipx** | CLI package manager | `curl -fsSL https://astral.sh/uv/install.sh \| sh` or `pip install pipx && pipx ensurepath` |

### Custom Install Location

```bash
IMAGE_TO_EDITABLE_PPT_DIR=~/my-path curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
```

### Uninstall

```bash
rm -rf ~/.image-to-editable-ppt-skill
uv tool uninstall image-to-editable-ppt-cli   # or: pipx uninstall image-to-editable-ppt-cli
```

---

## Usage

### Agent / Skills Registry (OpenAI Codex)

For Codex or compatible agent runtimes that support the `npx skills` registry:

```bash
npx -y skills@latest add a-green-hand-jack/image-to-editable-ppt-skill \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
```

Then install the CLI from the skill directory:

```bash
uv tool install --force ~/.image-to-editable-ppt-skill/cli
# or: pipx install --force --editable ~/.image-to-editable-ppt-skill/cli
editppt doctor
```

### CLI Quick Start

```bash
# 1. Prepare a run from input images / PDF / PPTX
editppt prepare slides.pdf

# 2. Rebuild pages (single-page: local; multi-page: dispatched workers)
editppt run next <run-dir>

# 3. Record validated page results
editppt run record <run-dir> --page page_001 --agent-id <id>

# 4. Finalize into a single .pptx
editppt run finalize <run-dir>
```

Full command reference: [`references/cli-helper.md`](references/cli-helper.md)

---

## How It Works

The skill decomposes each slide image into a structured manifest of positioned objects (text boxes, shapes, images, tables, formulas), then rebuilds an editable `.pptx` from that manifest.

```
Input (image/PDF/PPTX)
  │
  ├─ editppt prepare ──▶ run dir + text hints
  │
  ├─ Page workers ──────▶ manifest.json + page.pptx per page
  │
  ├─ editppt run record ──▶ validation + state tracking
  │
  └─ editppt run finalize ─▶ final editable .pptx
```

Key concepts:

- **Manifest-driven**: `manifest.json` is the single source of truth for every page's object layout.
- **Deterministic validation**: `editppt run record` validates structure before accepting any page.
- **Resumable runs**: every state transition goes through CLI commands — never hand-write state JSON.
- **Image backends**: built-in agent `image_gen.imagegen` tool first, then Codex OAuth, then user-configured OpenAI-compatible API.

---

## Repository Structure

```
├── SKILL.md                  # Skill definition & workflow contract
├── install.sh                # One-command installer
├── cli/                      # editppt CLI (Python)
│   ├── pyproject.toml
│   └── editppt/
│       ├── cli.py            # Entry point
│       └── runtime/          # All CLI subcommands
├── prompts/
│   └── page-worker.md        # Template for page-worker prompts
├── references/
│   ├── cli-helper.md         # Command reference & examples
│   ├── manifest-schema.md    # JSON field contracts
│   └── page-decision-tree.md # Object decision rules
├── scripts/
│   └── build-page-worker-prompt.py
└── agents/
    └── openai.yaml           # Codex agent interface
```

---

## Updating

Re-run the installer — it will pull the latest `main` and reinstall the CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
```

Or manually:

```bash
cd ~/.image-to-editable-ppt-skill && git pull
uv tool install --force ./cli
editppt doctor
```

---

## License

MIT
