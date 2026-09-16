---
name: image-to-editable-ppt
description: Reconstruct existing scientific figures, technical diagrams, slide screenshots, PDFs, and image-based PPT/PPTX into object-level editable PowerPoint while preserving source layout and supplied speaker notes. Use for image-to-PPT reconstruction, not authoring a new presentation from scratch.
---

# Image to Editable PPT

> Responsibility: guide the reconstructing agent from source input to editable PPTX. Maintain workflow boundaries and reference routing; keep detailed object rules in the linked references.

Use a vision-capable agent to identify source objects and the `editppt` CLI to prepare, build, validate, and assemble them. Text and structural geometry become native objects; complex artwork remains independently selectable image assets. Formula rendering preserves LaTeX source, not native equation editability. Never describe a selectable bitmap as fully editable vector artwork.

## Fast path: an existing PPTX

If the user already has a completed PPT/PPTX and only requests PDF export, do
not start image preparation, page workers, formula reconstruction, or visual
rebuilding. Run the deterministic conversion directly:

```bash
editppt export-pdf input.pptx --out figure.pdf --json
```

This path only needs a local LibreOffice-compatible renderer. It validates a
fresh PDF and reports the renderer and output path. The longer vision-agent
workflow is required only when the input is a raster/PDF/image-based deck and
an editable PPTX must be reconstructed first.

## Read by task

- [references/cli-helper.md](references/cli-helper.md): installation and public commands.
- [references/page-decision-tree.md](references/page-decision-tree.md): background, foreground, text, formulas, tables, paths, and fix-versus-warning rules.
- [references/manifest-schema.md](references/manifest-schema.md): source coordinates, page/deck state, asset provenance, backend policy, and validation contracts.
- [references/render-validation.md](references/render-validation.md): inspect the actual PPTX rendering before visual acceptance.
- [prompts/page-worker.md](prompts/page-worker.md): page ownership and reconstruction template, expanded by `scripts/build-page-worker-prompt.py`.

## Execution boundaries

Use the existing `editppt` command surface. All run/page state transitions go through the CLI; never manufacture state JSON or passing validation. `manifest.json` is the authoritative build source for both page PPTX and final assembly.

Use the model's native image inspection and reasoning to infer layout and correct visible differences. CLI operations support concrete workflow needs such as building and rendering artifacts; do not add a parallel layout solver, model coordinator, or ad-hoc monitoring wrapper. Object decomposition and spatial fidelity are separate requirements: a complete inventory does not establish alignment.

Inspect the input before reconstructing. Inventory each visible label, arrow, connector, panel, and foreground object with source-pixel geometry and stable IDs. Preserve repeated instances separately. The decision tree owns object classification and source rules: do not replace foreground artwork with approximate primitives, substitute source crops for the required separation workflow, or flatten a whole panel/page into an image. Never hide editable text off canvas or over a duplicate raster label.

A single-page run is reconstructed by the current agent after `dispatch --local`. In `codex exec`, that agent is the headless process itself: it reads the PNG, writes the manifest, checks renders, and delivers the final PPTX without asking the caller to supply object annotations or perform the conversion steps. Multi-page runs use actual page workers when the agent runtime supports and permits them. Each worker owns exactly one page directory; the parent owns orchestration, source-versus-result review, record and finalize. If worker execution is unavailable for a multi-page run, report the concrete limitation. This skill does not install or launch another agent runtime.

Use only the task's inputs and user-configured services. Respect local-only/confidential constraints and runtime permissions. Conversion authorization does not authorize sending unrelated files or changing global providers. Keep secrets out of prompts, manifests, logs, and outputs. Do not hard-code a machine, endpoint, or vision model into the workflow.

The image backend is runtime configuration, not part of the skill's identity. For a provider-independent headless run, set `EDITPPT_IMAGE_BACKEND=api`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `IMAGE_TO_EDITABLE_PPT_IMAGE_MODEL` in the child process. Use `EDITPPT_IMAGE_BACKEND=codex-oauth` only when device-local Codex OAuth Images is intentionally authorized; default `auto` is convenient for interactive development but must not be assumed by a portable run. Never print or persist the key.

## 1. Prepare

Check `editppt --help`; follow the CLI reference if installation is needed.

```bash
editppt prepare <input...> --job-dir <absolute-run-dir>
```

Prepare writes deck/page jobs, notes, source images, requests, and advisory text hints. Read each page's request and copy its canvas/content box into the manifest. Different page proportions in a deck share one canvas; for independent benchmark figures, use one run per figure.

OCR is optional. With no configured token, continue using the offline geometry hints and direct visual transcription; do not interrupt to require signup, promise free quotas, or claim geometry hints recognize text. Empty or inaccurate hints never justify omitting text. Measure glyph height and preserve source text levels as the page prompt specifies. Configured OCR may be used within the user's data-processing constraints; report failures and distinguish offline hints from recognized text. `--no-text-hints` skips hint generation when required. Never ask the user to paste credentials into chat.

For required image jobs, preflight the callable tools before writing a manifest: identify whether a local/built-in image editor is available, whether the configured external backend is reachable, and whether the current task authorizes sending source pixels to it. Record the result in the run evidence. If the runtime exposes the recorded built-in image tool, prepare with `--image-backend builtin-imagegen`; otherwise use the CLI backend contract. Run page-local image jobs serially. Built-in first and allowed CLI fallback events/order are defined by `page_request.json.image_backend` and the manifest reference. Never invent tool availability, provenance, or successful generation.

If an image backend is unavailable, do not block an entire page solely because of simple flat pictograms that can be represented by a small, source-grounded set of native PowerPoint primitives. Such objects may use native fallback only when their geometry, count, colors, and placement are unambiguous; record `source_fidelity: approximate`, the backend failure, and the affected object IDs, and report the limitation. Complex artwork, photos, textured marks, logos, and objects whose identity would be materially changed remain blocked rather than approximated. A backend outage must therefore degrade only the affected objects, not silently flatten or abandon an otherwise reconstructable page.

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

Follow the prompt's decision order: inventory and background decisions, foreground asset separation, native elements. Preserve the source layout relationships described in the decision tree's "Source layout anchors" section while placing objects. Import/process generated assets through the CLI so their actual producer and hashes are recorded. Build from the manifest, inspect its program preview, then inspect the actual PPTX render using the render reference. Check text, object coverage, connector endpoints, repeated symbols, layering, fonts, and clipped edges against the source.

`preview.png` is a Pillow approximation; structural validation and self-declared counts do not prove rendering fidelity. Record real rendering evidence and unresolved differences. Missing rendering tools or failed conversion must remain explicit; never report visual acceptance based only on the program preview.

Use the existing visual audit fields and validation contract. Inspect each image asset against its source identity. Repair concrete failures and rebuild/re-render affected outputs; do not repeat unchanged checks or regenerate compliant assets.

For pages containing formulas, follow the decision tree's engine/converter recovery before treating a tool failure as terminal. Never equate a structurally valid draft with complete reconstruction when a source formula is absent or replaced by an unauthorized text approximation.

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

By default, final assembly emits two slides for each input page in order: the original raster source on the first slide and the editable reconstruction on the second slide. The source slide is a comparison reference and is intentionally not claimed to be editable. Page-local manifests and validation continue to cover the editable reconstruction slide.

Report the final PPTX path, structural result, actual rendering result, editable object types, remaining bitmap/formula regions, and unresolved differences. If blocked, report only existing artifacts and the concrete failure. Do not turn unrun or failed cases into success.

After a completed PPTX is accepted, export a paper-ready PDF with the public CLI:

```bash
editppt export-pdf <final.pptx> --out <figure.pdf> --json
```

This is a separate post-finalize conversion step. Confirm the reported renderer and PDF file before treating the PDF as delivered. Native text and shapes can remain vector in the PDF; complex artwork that was intentionally retained as a bitmap remains raster.

## Updating

Update through the user's installation channel. Install the CLI from the repository root (`uv tool install --force <repo-root>`) or the released wheel, refresh the registered skill, and restart skill discovery. Product resources are shipped together under `editppt/skills/image-to-editable-ppt/`; the former `<skill-root>/cli` layout no longer exists.
