# Page Reconstructor Prompt Template

Placeholders of the form `{{NAME}}` are filled by `scripts/build-page-worker-prompt.py`.

```text
Rebuild one page for image-to-editable-ppt.

Run dir: {{RUN_DIR}}
Page id: {{PAGE_ID}}
Page dir: {{PAGE_DIR}}
Source image: {{SOURCE_IMAGE}}

You own only this Page dir. Do not edit deck_manifest.json, page_jobs.json, notes_manifest.json, final outputs, the original input, or any other page directory.

Read references by task, before acting on their rules. All reference paths below are under {{SKILL_ROOT}}/references/; do not reread unchanged sections already available in this execution.
- Start with page_request.json and page-decision-tree.md's introduction, "Common Failure Mode: False Progress", and "Pre-Decision: Page Inventory". Inspect the source and build the inventory, then read sections 1 and 2 for object-source decisions.
- Before native reconstruction, read section 3.1 for text; read sections 3.2-3.6 when the inventory contains their formulas, structural objects/tables, corners, decorated text, or groups. Read "Final Self-Check" and "Fix versus Warning" before acceptance or a repair decision.
- Read manifest-schema.md's page_request.json and pages/page_NNN/manifest.json contracts before writing the manifest, loading applicable object contracts such as "Native tables". Before image jobs read the image_backend and imagegen-jobs.json contracts; for region splitting read "Asset sheet regions and split reports". Before returning read the validation.json and page_result.json contracts. Deck-state and notes contracts are outside your ownership.
- Use cli-helper.md for the commands needed now: "Page Build Commands", and "Image Backend Commands", "Asset Processing Commands", or "Formula Commands" when applicable. Do not load unrelated install or orchestration instructions.
- Before visual acceptance, read render-validation.md. The program preview is not an actual rendering of page.pptx; verify the PPTX with an available presentation renderer and retain that evidence.

Hard rules (reminders; authoritative details remain in the references):
1. Separate foreground visuals through image editing; backend fallback never permits source crops or approximate substitutes — page-decision-tree.md section 2.
2. Decide background, then foreground, then native elements; consume text hints only after steps 1-2 decisions — page-decision-tree.md introduction and section 3.1.
3. Build from manifest.json with the deterministic runtime; preserve source-pixel geometry and request canvas — manifest-schema.md's page_request.json and manifest.json contracts.
4. Execute the recorded image backend contract, including built-in first, valid result import, and permitted fallback events — manifest-schema.md's image_backend contract.
5. Structural validation never waives object-source rules — page-decision-tree.md "Common Failure Mode: False Progress".
6. Text sizing without OCR: `text_hints.json` is ADVISORY and may be empty. Read every label from the source image yourself, and set each text box's `font_size` from the measured CAPITAL/ascender glyph height in source pixels, not from the text-box height. On the default 96 px/in canvas, `font_size_pt ≈ capital_glyph_height_px` (more generally `font_size_pt ≈ glyph_height_px × 72 / px_per_inch / 0.7`). Use exactly one size per text level. Deriving the size from the bounding-box height, or leaving an empty/geometry-only hint set at a default size, is wrong and must be corrected before validation.
7. The inventory is one structured row per visible source object. Every row needs a unique `id`, `role`, `object_type`, `source_box_px`, and `representation_ids`. Never combine separate labels into one large text box, and never use 1x1 or off-canvas text as a placeholder. For every arrow, connector, decision branch, icon, repository/document mark, brace, panel, person, robot, plant, device, sticker, or illustration, record a source object id and rebuild it as a separate selectable object. Semantic foreground objects must use image assets produced by the asset-sheet/image-edit workflow; do not replace them with native geometric approximations. Set `visual_audit.source_visual_object_ids` to the exact inventory id set and derive `expected_semantic_visuals` from the inventory. A zero semantic count is valid only when the source inventory explicitly proves that the page contains no semantic foreground visual objects.
8. Every visible text box must include `font_size_source: "measured"` and a source-pixel `box_px` that fits the actual label, not the surrounding card or panel. Do not let `fit_text` silently shrink a text level below the measured source size; split the box or correct its geometry instead.

Recovery: read any previous validation failure before editing. Verify reusable artifacts against the current source, page request/backend contract, manifest links, and imagegen-jobs.json provenance (paths/hashes); inspect their visual content where relevant. Reuse compliant artifacts and repair only failed or dependent parts. Rebuild from the inventory only when the source or object-source decisions are invalid. Never flip leftover validation to passed or return stale outputs without validating the current artifact set.

Execution:
1. Record the inventory and background/foreground decisions, then execute necessary image jobs under page-decision-tree.md sections 1-2. Page-local image jobs remain serial. Import and process selected image outputs using the image-job contract.
   For dense/repeated/overlapping foreground objects, split the inventory into small serial asset sheets and verify each sheet against its exact source-instance IDs before import; reject merged subjects, missing repeated marks, or wrong order.
2. Reconstruct native elements under the applicable section 3 rules and write manifest.json using its field contract.
3. Run `editppt page build {{PAGE_DIR}}`, then `editppt page contact-sheet {{PAGE_DIR}}`.
4. Render page.pptx using render-validation.md and compare that actual render against source.png, including text, connectors, repeated objects, and asset edges. Record commands, renderer, paths, and differences in visual_audit.review_notes. Perform the Final Self-Check and run `editppt page validate {{PAGE_DIR}}`. Fix page-local issues yourself; after a change rebuild and re-render the affected outputs. Once the current outputs pass, return without another unchanged build/QA cycle. If rendering is unavailable or fails, report that boundary; do not claim visual acceptance from preview.png alone.

Required outputs: manifest.json, imagegen-jobs.json, page.pptx, preview.png, split_assets_contact.png, validation.json, page_result.json. Validation and page-result shapes are owned by manifest-schema.md; success requires top-level validation `passed: true` and the required outputs. If any source visual object lacks a representation, or if the preview omits/approximates one, write `passed: false`; do not hide the omission by lowering the expected count.

Routine repairs and recorded backend fallbacks require no extra user confirmation. Respect runtime-required approvals and user data-processing constraints. OCR is optional; offline hints require visual transcription. Do not retry the same failing tool with unchanged inputs and conditions. If a hard requirement remains blocked after applicable fallbacks, write validation.json with `passed: false` and the concrete cause/error, plus page_result.json referencing only artifacts that exist. Preserve progress; do not fabricate outputs, substitute an approximate page, or request an unconditional fresh reconstruction.

Return only available artifact paths (omit missing artifacts on failure):
page_manifest=`<absolute path>`
page_pptx=`<absolute path>`
preview=`<absolute path>`
contact_sheet=`<absolute path>`
validation=`<absolute path>`
page_result=`<absolute path>`
```
