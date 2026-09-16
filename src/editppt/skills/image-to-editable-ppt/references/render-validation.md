# Actual PPTX render validation

> Responsibility: guide source-versus-PPTX visual review and evidence recording. Maintain real-render and structural-validation boundaries; do not present model judgment as an automated similarity test.

`editppt page build` writes a native PPTX and a Pillow-generated `preview.png`. The preview helps debug manifest geometry but does not exercise Office font substitution, text layout, clipping, or rendering of DrawingML. `editppt page validate` checks package/object structure; it does not compare pixels or establish visual fidelity.

Use an available real presentation renderer (LibreOffice or PowerPoint) to inspect the current PPTX. Discover its executable rather than hard-coding an OS-specific path. If it is unavailable, preserve the files and report `render unverified`; do not invent a successful render or conflate it with structural pass. This procedure requires no new model backend.

## Page inspection

With LibreOffice and Poppler on PATH, from the owned page directory:

```bash
command -v soffice
command -v pdftoppm
soffice --version
mkdir render-001
soffice --headless --convert-to pdf --outdir "$PWD/render-001" "$PWD/page.pptx"
test -s render-001/page.pdf
pdftoppm -png -singlefile -r 144 render-001/page.pdf render-001/page
test -s render-001/page.png
```

Use a fresh numbered render directory after each changed build, so a failed converter cannot leave an old PDF/PNG masquerading as the current result. Check command output as well as file existence: a converter may exit successfully without creating the requested file. Never overwrite `preview.png` with the real render; preserve the two evidence sources separately. If a renderer reports a file lock, use its supported isolated profile or close the owning application only when authorized.

For a profile conflict, use a new profile under the owned run, e.g. `-env:UserInstallation=file://$PWD/render-001/lo-profile`, instead of changing `HOME`, deleting shared profiles, or using fixed global temporary paths. Linux sandboxing can also prevent LibreOffice startup even with a writable profile. On permission errors or repeated exit 1 without a PDF, request the runtime's normal approval for that specific render command when supported; otherwise report the renderer as blocked. Do not keep changing paths or disabling sandbox protections. A headless launcher must configure its approval policy before starting; the skill cannot grant permissions.

Inspect the resulting image and `source.png` at comparable display scale. Respect `content_box` when the source is letterboxed; do not stretch a source image to force pixel agreement. Check:

- Text content, glyph sizes, line breaks, superscripts, clipping, font substitution, and any CJK missing glyphs.
- Every connector endpoint, arrowhead, branch, dashed/curved line, and repeated icon instance.
- Container corners, gradients, colors, spacing, source aspect ratio, and layer order.
- Independent image boundaries, shadows, fine edges, missing/merged objects, and duplicate labels in raster layers.

Record the actual renderer/version, command, current PPTX SHA-256 (`sha256sum page.pptx`, or `shasum -a 256 page.pptx` on macOS), artifact paths, and observed differences in `visual_audit.review_notes`. These are evidence, not automatic acceptance flags. The existing audit counts and structure checks still apply. Do not assert `independent_review` without a fresh source-versus-result inspection.

### Alignment correction

Use the agent's native image viewer to inspect both the source and actual render, first as whole pages and then at the affected regions. Compare the source content region at the same aspect ratio and comparable scale; slide letterboxing is not a layout error. Do not infer source-pixel corrections directly from a render at a different resolution.

Review from large relationships to small ones:

1. Overall layout: panel bounds, page margins, relative widths/heights, and major gaps. Shared displacement across a group suggests a common anchor error; check the coordinate mapping before adjusting every object separately.
2. Within groups: shared edges/centerlines, repeated spacing, icon-to-label offsets, and connector attachments. Correct the common anchor and its dependent objects together while preserving source asymmetry.
3. Text and artwork: visible baselines, line breaks, centering, and visible asset bounds. If boxes align but glyphs do not, inspect font substitution and text alignment; if the PNG box aligns but the icon does not, inspect transparent padding. Do not compensate for either by moving an otherwise correct panel.

For each material discrepancy, note the object IDs, source relationship, observed drift, and correction in `visual_audit.review_notes`. Use `misaligned_object_ids` for unresolved displacement and clear an ID only after inspecting the rebuilt render. Structural success or complete object counts cannot establish visual alignment. If a correction makes no progress, revisit its cause; if tools or source evidence prevent further correction, report the unresolved difference instead of claiming visual acceptance.

Fix the specific discrepancy in the manifest or asset, rebuild, and repeat the affected render. No fixed number of correction passes is required. Stop when the source-grounded checks pass with only documented allowable differences.

## Final deck

After finalize, render the exact final PPTX in another fresh directory and export all PDF pages with `pdftoppm -png` (omit `-singlefile`). By default each input produces a pair: source raster on slide `2n-1`, editable reconstruction on slide `2n`. Verify both slides preserve the same content placement; compare the even-numbered slide against the accepted page render. The reference raster is intentionally non-editable and must not count toward editable object coverage. Existing page-local object checks need not be repeated when the objects and their evidence are unchanged. Report final structure validation and actual render validation separately.
