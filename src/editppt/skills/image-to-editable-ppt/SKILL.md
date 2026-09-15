---
name: image-to-editable-ppt
description: Reconstruct existing scientific figures, technical diagrams, slide screenshots, PDFs, and image-based PPT/PPTX into object-level editable PowerPoint while preserving source layout and supplied speaker notes. Use for image-to-PPT reconstruction, not authoring a new presentation from scratch.
---

# Image to Editable PPT

Use a vision-capable agent to identify source objects and the `editppt` CLI to prepare, build, validate, and assemble them. Text and structural geometry become native objects; complex artwork remains independently selectable image assets. Formula rendering preserves LaTeX source, not native equation editability. Never describe a selectable bitmap as fully editable vector artwork.

## Read by task

- [references/cli-helper.md](references/cli-helper.md): installation and public commands.
- [references/page-decision-tree.md](references/page-decision-tree.md): background, foreground, text, formulas, tables, paths, and fix-versus-warning rules.
- [references/manifest-schema.md](references/manifest-schema.md): source coordinates, page/deck state, asset provenance, backend policy, and validation contracts.
- [references/render-validation.md](references/render-validation.md): inspect the actual PPTX rendering before visual acceptance.
- [prompts/page-worker.md](prompts/page-worker.md): page ownership and reconstruction template, expanded by `scripts/build-page-worker-prompt.py`.

## Execution boundaries

Use the existing `editppt` command surface. All run/page state transitions go through the CLI; never manufacture state JSON or passing validation. `manifest.json` is the authoritative build source for both page PPTX and final assembly.

Inspect the input before reconstructing. Inventory each visible label, arrow, connector, panel, and foreground object with source-pixel geometry and stable IDs. Preserve repeated instances separately. The decision tree owns object classification and source rules: do not replace foreground artwork with approximate primitives, substitute source crops for the required separation workflow, or flatten a whole panel/page into an image. Never hide editable text off canvas or over a duplicate raster label.

A single-page run is reconstructed by the current agent after `dispatch --local`. In `codex exec`, that agent is the headless process itself: it reads the PNG, writes the manifest, checks renders, and delivers the final PPTX without asking the caller to supply object annotations or perform the conversion steps. Multi-page runs use actual page workers when the agent runtime supports and permits them. Each worker owns exactly one page directory; the parent owns orchestration, source-versus-result review, record and finalize. If worker execution is unavailable for a multi-page run, report the concrete limitation. This skill does not install or launch another agent runtime.

Use only the task's inputs and user-configured services. Respect local-only/confidential constraints and runtime permissions. Conversion authorization does not authorize sending unrelated files or changing global providers. Keep secrets out of prompts, manifests, logs, and outputs. Do not hard-code a machine, endpoint, or vision model into the workflow.

## 1. Prepare

Check `editppt --help`; follow the CLI reference if installation is needed.

```bash
editppt prepare <input...> --job-dir <absolute-run-dir>
```

Prepare writes deck/page jobs, notes, source images, requests, and advisory text hints. Read each page's request and copy its canvas/content box into the manifest. Different page proportions in a deck share one canvas; for independent benchmark figures, use one run per figure.

OCR is optional. With no configured token, continue using the offline geometry hints and direct visual transcription; do not interrupt to require signup, promise free quotas, or claim geometry hints recognize text. Empty or inaccurate hints never justify omitting text. Measure glyph height and preserve source text levels as the page prompt specifies. Configured OCR may be used within the user's data-processing constraints; report failures and distinguish offline hints from recognized text. `--no-text-hints` skips hint generation when required. Never ask the user to paste credentials into chat.

For required image jobs, inspect the callable tools. If the runtime exposes the recorded built-in image tool, prepare with `--image-backend builtin-imagegen`; otherwise use the CLI backend contract. Run page-local image jobs serially. Built-in first and allowed CLI fallback events/order are defined by `page_request.json.image_backend` and the manifest reference. Never invent tool availability, provenance, or successful generation. If compliant separation remains impossible, preserve progress and report the affected objects.

## 2. Claim or dispatch pages

```bash
editppt run next <run>
python3 <skill-root>/scripts/build-page-worker-prompt.py <run> --page page_001 --out <absolute-page-dir>/worker-prompt.md
```

For `stage=rebuild_page_locally`, claim before writing reconstruction artifacts:

```bash
editppt run dispatch <run> --page page_001 --agent-id main --prompt-file <absolute-page-dir>/worker-prompt.md --local
```

Read the generated prompt and reconstruct locally. For `stage=dispatch_pages`, generate the prompt, spawn a real worker, then record its actual ID:

```bash
editppt run dispatch <run> --page <page_id> --agent-id <worker-id> --prompt-file <absolute-page-dir>/worker-prompt.md
```

Prompt paths must be absolute. Respect the run's concurrency limit and the runtime's available slots. `stage=wait` means active leases: wait or inspect status. Do not replace or reset a worker merely because it is slow. The parent must not write another worker's reconstruction artifacts.

## 3. Reconstruct and verify

Follow the prompt's decision order: inventory and background decisions, foreground asset separation, native elements. Import/process generated assets through the CLI so their actual producer and hashes are recorded. Build from the manifest, inspect its program preview, then inspect the actual PPTX render using the render reference. Check text, object coverage, connector endpoints, repeated symbols, layering, fonts, and clipped edges against the source.

`preview.png` is a Pillow approximation; structural validation and self-declared counts do not prove rendering fidelity. Record real rendering evidence and unresolved differences. Missing rendering tools or failed conversion must remain explicit; never report visual acceptance based only on the program preview.

Use the existing visual audit fields and validation contract. Inspect each image asset against its source identity. Repair concrete failures and rebuild/re-render affected outputs; do not repeat unchanged checks or regenerate compliant assets.

The parent reviews source versus rendered page (and separated assets when relevant), then records:

```bash
editppt run record <run> --page <page_id> --agent-id <owner-id>
```

Record rejects incomplete page artifacts, invalid manifests, mismatched owners, or a validation report without top-level boolean `passed: true`. It checks structural evidence; it does not perform an independent visual judgment.

## 4. Recover and finalize

For validation failure, send the evidence to the same owner and repair the affected artifacts. Reuse valid assets after checking provenance. Reset only for user cancellation, explicit terminal-state evidence, or repeated failed reachability checks with no page-local progress:

```bash
editppt run reset <run> --page <page_id> --agent-id <owner-id> --confirm-lost
```

Recorded pages may be reset without a lost-worker claim. Never retry an unchanged failed operation indefinitely.

When `next` returns `stage=finalize`:

```bash
editppt run finalize <run>
```

Finalize rebuilds the deck from recorded page manifests and checks slide order/count, package relationships, source/asset hashes, and notes. Inspect the final PPTX through a real renderer as described in the render reference; final assembly is a distinct artifact from page previews.

Report the final PPTX path, structural result, actual rendering result, editable object types, remaining bitmap/formula regions, and unresolved differences. If blocked, report only existing artifacts and the concrete failure. Do not turn unrun or failed cases into success.

## Updating

Update through the user's installation channel. Install the CLI from the repository root (`uv tool install --force <repo-root>`) or the released wheel, refresh the registered skill, and restart skill discovery. Product resources are shipped together under `editppt/skills/image-to-editable-ppt/`; the former `<skill-root>/cli` layout no longer exists.
