# Actual PPTX render validation

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

Inspect the resulting image and `source.png` at comparable display scale. Respect `content_box` when the source is letterboxed; do not stretch a source image to force pixel agreement. Check:

- Text content, glyph sizes, line breaks, superscripts, clipping, font substitution, and any CJK missing glyphs.
- Every connector endpoint, arrowhead, branch, dashed/curved line, and repeated icon instance.
- Container corners, gradients, colors, spacing, source aspect ratio, and layer order.
- Independent image boundaries, shadows, fine edges, missing/merged objects, and duplicate labels in raster layers.

Record the actual renderer/version, command, current PPTX SHA-256 (`sha256sum page.pptx`, or `shasum -a 256 page.pptx` on macOS), artifact paths, and observed differences in `visual_audit.review_notes`. These are evidence, not automatic acceptance flags. The existing audit counts and structure checks still apply. Do not assert `independent_review` without a fresh source-versus-result inspection.

Fix the specific discrepancy in the manifest or asset, rebuild, and repeat the affected render. No fixed number of correction passes is required. Stop when the source-grounded checks pass with only documented allowable differences.

## Final deck

After finalize, render the exact final PPTX in another fresh directory and export all PDF pages with `pdftoppm -png` (omit `-singlefile`). Verify page count/order and inspect assembly-wide layout differences against the accepted page renders. Existing page-local object checks need not be repeated when the objects and their evidence are unchanged. Report final structure validation and actual render validation separately.
