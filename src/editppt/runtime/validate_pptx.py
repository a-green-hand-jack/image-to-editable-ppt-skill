#!/usr/bin/env python3
import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from build_pptx_from_manifest import TEXT_ALIGNMENTS, TEXT_VERTICAL_ALIGNMENTS, normalize_manifest, slide_xml, source_slide_manifest


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

ALLOWED_SOURCE_TYPES = {
    "asset-sheet-separated",
    "imagegen",
    "latex-rendered-formula",
    "user-provided",
    "user-approved-rasterization",
    "native-approximate",
}
REQUIRED_QUALITY_CHECKS = {
    "font_size_calibrated",
    "visual_inventory_matched",
    "background_strategy_checked",
    "shape_corner_geometry_checked",
}
FOREGROUND_TERMS = {
    "badge",
    "decorative",
    "foreground",
    "hand-drawn",
    "icon",
    "illustration",
    "image block",
    "logo",
    "mark",
    "photo",
    "pictogram",
    "screenshot",
    "semantic",
    "sticker",
    "symbol",
    "trend",
    "visual object",
    "前景",
    "图标",
    "照片",
    "截图",
    "徽章",
    "贴纸",
    "语义",
    "视觉对象",
}
NON_FOREGROUND_TERMS = {
    "background",
    "clean base",
    "formula",
    "latex",
    "native structural",
    "structural shape",
    "背景",
    "公式",
    "结构",
}
ASSET_SHEET_TERMS = {
    "asset-sheet",
    "asset sheet",
    "asset_sheet",
    "image edit",
    "imagegen",
    "separated",
    "source-faithful",
    "source faithful",
    "split",
    "分离",
}
SEMANTIC_FOREGROUND_TYPES = {
    "icon", "pictogram", "symbol", "logo", "illustration", "person", "robot",
    "plant", "animal", "device", "photo", "screenshot", "sticker", "badge",
    "decorative-mark", "decorative", "semantic-visual",
}
FORBIDDEN_FOREGROUND_FALLBACK_TERMS = {
    "approximate",
    "approximation",
    "approximated",
    "crop",
    "cropped",
    "direct crop",
    "direct source",
    "emoji",
    "fallback",
    "native approximation",
    "source crop",
    "source snippet",
    "text symbol",
    "warning only",
    "warning_only",
    "近似",
    "裁切",
    "裁剪",
    "降级",
}


def read_manifest(path):
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def contains_any(text, terms):
    # English terms are words, not substrings (e.g. mark != benchmark).
    return any(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text.lower()) for term in terms)


def gradient_contract_violations(item, field):
    violations = []
    gradient = item.get(field)
    if gradient is None:
        return violations
    if not isinstance(gradient, dict):
        return [{"field": field, "reason": "gradient must be an object"}]
    stops = gradient.get("stops")
    if not isinstance(stops, list) or len(stops) < 2:
        violations.append({"field": field + ".stops", "reason": "gradient requires at least two stops"})
        return violations
    positions = []
    for index, stop in enumerate(stops):
        if not isinstance(stop, dict) or "position" not in stop or "color" not in stop:
            violations.append({"field": f"{field}.stops[{index}]", "reason": "gradient stops require position and color"})
            continue
        try:
            position = float(stop["position"])
            if not 0 <= position <= 100:
                raise ValueError
            positions.append(position)
            color = str(stop["color"]).lstrip("#")
            if len(color) != 6 or any(char not in "0123456789abcdefABCDEF" for char in color):
                raise ValueError
        except (TypeError, ValueError):
            violations.append({"field": f"{field}.stops[{index}]", "reason": "gradient stop position must be 0-100 and color must be six-digit hex"})
    if positions != sorted(positions):
        violations.append({"field": field + ".stops", "reason": "gradient stop positions must be nondecreasing"})
    try:
        angle = float(gradient.get("angle", 0))
        if not 0 <= angle < 360:
            raise ValueError
    except (TypeError, ValueError):
        violations.append({"field": field + ".angle", "reason": "gradient angle must be in [0, 360) degrees"})
    return violations


def visual_item_path(item):
    for key in ("path", "asset", "asset_path", "image", "image_path", "corresponding_asset"):
        value = item.get(key) if isinstance(item, dict) else None
        if isinstance(value, str) and value.strip():
            return Path(value).as_posix()
    return None


def is_foreground_visual_item(item):
    if isinstance(item, dict):
        role = item.get("role")
        if role in {"foreground", "background", "structure", "formula"}:
            return role == "foreground"
        # Free-form notes, file names and provenance explanations are not types.
        text = str(item.get("object_type") or item.get("description") or "")
    else:
        text = str(item)
    if contains_any(text, NON_FOREGROUND_TERMS):
        return False
    return contains_any(text, FOREGROUND_TERMS)


def has_forbidden_decision(decision):
    # Legacy decisions may describe the method in prose; ignore simple negative
    # statements, but never mine arbitrary notes for forbidden keywords.
    text = str(decision).lower()
    terms = "|".join(re.escape(term) for term in sorted(FORBIDDEN_FOREGROUND_FALLBACK_TERMS, key=len, reverse=True))
    text = re.sub(r"\b(?:no|not|without|never)(?:\s+using)?\s+(?:" + terms + r")(?![a-z0-9])", "", text)
    text = re.sub(r"(?:没有|未使用|不使用|无需|禁止)(?:" + terms + r")", "", text)
    return contains_any(text, FORBIDDEN_FOREGROUND_FALLBACK_TERMS)


def foreground_asset_contract_violations(manifest):
    violations = []
    allowed_foreground_sources = {"asset-sheet-separated", "imagegen", "native-approximate"}
    provenance_by_path = {
        Path(entry["path"]).as_posix(): entry
        for entry in manifest.get("asset_provenance", [])
        if isinstance(entry, dict) and entry.get("path")
    }
    foreground_paths = set()

    for index, item in enumerate(manifest.get("visual_inventory", [])):
        field = f"visual_inventory[{index}]"
        if isinstance(item, dict) and "role" in item and item["role"] not in {"foreground", "background", "structure", "formula"}:
            violations.append({"field": field + ".role", "reason": "role must be foreground, background, structure, or formula"})
        if not is_foreground_visual_item(item):
            continue
        structured = isinstance(item, dict) and any(key in item for key in ("role", "object_type", "source_type"))
        decision = item.get("decision", "") if isinstance(item, dict) else item
        declared_source = item.get("source_type") if isinstance(item, dict) else None
        if (not structured and has_forbidden_decision(decision)) or (declared_source is not None and declared_source not in allowed_foreground_sources):
            violations.append({"field": field, "reason": "foreground visual decisions must use separated assets or an explicitly recorded native-approximate fallback"})
        path = visual_item_path(item)
        if path:
            foreground_paths.add(path)
            provenance = provenance_by_path.get(path)
            if not provenance or provenance.get("source_type") not in allowed_foreground_sources:
                violations.append({"field": field, "path": path, "reason": "foreground visual objects require matching asset-sheet-separated or imagegen provenance"})
            elif declared_source is not None and declared_source != provenance.get("source_type"):
                violations.append({"field": field + ".source_type", "path": path, "reason": "source_type must match the linked asset provenance"})
        elif structured and declared_source != "native-approximate":
            violations.append({"field": field, "reason": "structured foreground visual objects require an asset path unless native-approximate is explicitly recorded"})
        elif not contains_any(str(decision), ASSET_SHEET_TERMS) or not any(
            entry.get("source_type") in allowed_foreground_sources for entry in provenance_by_path.values()
        ):
            # Legacy inventories sometimes summarize several assets without paths.
            # Keep them readable, but a claim of separation alone is not evidence.
            violations.append({"field": field, "reason": "legacy foreground visual objects require an asset-sheet separation decision and matching permitted asset provenance"})

    for index, entry in enumerate(manifest.get("asset_provenance", [])):
        if not isinstance(entry, dict):
            continue
        path = Path(entry.get("path", "")).as_posix()
        if (path in foreground_paths or is_foreground_visual_item(entry)) and entry.get("source_type") not in allowed_foreground_sources:
            violations.append({"field": f"asset_provenance[{index}]", "path": path, "reason": "foreground asset provenance must use asset-sheet-separated or imagegen"})
    return violations


def visual_inventory_contract_violations(manifest):
    """Require a source-grounded, object-level inventory before visual QA passes."""
    violations = []
    inventory = manifest.get("visual_inventory", [])
    if not isinstance(inventory, list):
        return violations
    ids = []
    image_ids_by_path = {}
    for image in manifest.get("images", []):
        if isinstance(image, dict) and image.get("path") and image.get("id"):
            path = Path(image["path"]).as_posix()
            image_ids_by_path.setdefault(path, set()).add(str(image["id"]).strip())
    represented_ids = {
        str(item.get("id")).strip()
        for section in ("images", "shapes", "tables", "text_boxes")
        for item in manifest.get(section, [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    semantic_ids = []
    for index, item in enumerate(inventory):
        field = f"visual_inventory[{index}]"
        if not isinstance(item, dict):
            violations.append({"field": field, "reason": "new visual inventories must be structured objects"})
            continue
        object_id = str(item.get("id", "")).strip()
        if not object_id:
            violations.append({"field": field + ".id", "reason": "every source visual object needs a stable id"})
        elif object_id in ids:
            violations.append({"field": field + ".id", "reason": "visual object ids must be unique", "id": object_id})
        else:
            ids.append(object_id)
        role = item.get("role")
        if role in {"foreground", "structure"}:
            box = item.get("source_box_px") or item.get("box_px")
            if not isinstance(box, list) or len(box) != 4 or float(box[2]) < 2 or float(box[3]) < 2:
                violations.append({"field": field + ".source_box_px", "reason": "source visual objects require a positive source-pixel box"})
            reps = item.get("representation_ids")
            if not isinstance(reps, list) or not reps or not all(str(value).strip() for value in reps):
                violations.append({"field": field + ".representation_ids", "reason": "every source visual object must map to selectable PPT object ids"})
            else:
                missing_reps = sorted(set(str(value).strip() for value in reps) - represented_ids)
                if missing_reps:
                    violations.append({"field": field + ".representation_ids", "reason": "representation ids must resolve to positioned manifest objects", "missing": missing_reps})
        object_type = str(item.get("object_type", "")).strip().lower()
        is_semantic = role == "foreground" or object_type in SEMANTIC_FOREGROUND_TYPES
        if is_semantic:
            semantic_ids.append(object_id or f"inventory_{index}")
            if role != "foreground":
                violations.append({"field": field + ".role", "reason": "semantic visual objects must be foreground assets, not structural shapes"})
            path = visual_item_path(item)
            matching_ids = image_ids_by_path.get(path, set()) if path else set()
            if item.get("source_type") == "native-approximate":
                continue
            if not matching_ids:
                violations.append({"field": field, "reason": "semantic visuals require a matching manifest image asset with an id"})
            elif not isinstance(item.get("representation_ids"), list) or not matching_ids.intersection(item["representation_ids"]):
                violations.append({"field": field + ".representation_ids", "reason": "semantic visual representation must identify its matching image asset"})
    audit = manifest.get("visual_audit")
    if isinstance(audit, dict):
        declared_ids = audit.get("source_visual_object_ids")
        if not isinstance(declared_ids, list) or set(declared_ids) != set(ids):
            violations.append({"field": "visual_audit.source_visual_object_ids", "reason": "audit must enumerate exactly the source visual inventory ids"})
        if audit.get("expected_semantic_visuals") != len(semantic_ids):
            violations.append({"field": "visual_audit.expected_semantic_visuals", "reason": "semantic visual count must be derived from visual_inventory", "expected": len(semantic_ids)})
    return violations


def is_full_slide_image(item, slide):
    width = float(slide.get("width", 13.333))
    height = float(slide.get("height", 7.5))
    left = float(item.get("left", 0))
    top = float(item.get("top", 0))
    image_width = float(item.get("width", 0))
    image_height = float(item.get("height", 0))
    return (
        abs(left) <= 0.02
        and abs(top) <= 0.02
        and image_width >= width * 0.98
        and image_height >= height * 0.98
    )


def page_contract_violations(manifest):
    violations = []
    slide = manifest.get("slide", {})
    images = manifest.get("images", [])
    text_boxes = manifest.get("text_boxes", []) or manifest.get("tables", [])
    provenance_by_path = {
        Path(entry.get("path", "")).as_posix(): entry
        for entry in manifest.get("asset_provenance", [])
        if entry.get("path")
    }
    for image in images:
        path = Path(image.get("path", "")).as_posix()
        provenance = provenance_by_path.get(path, {})
        source_type = provenance.get("source_type")
        if is_full_slide_image(image, slide) and Path(path).name == "source.png" and text_boxes:
            violations.append(
                {
                    "field": "images",
                    "path": path,
                    "reason": "full-slide source.png background with editable text overlays causes baked-text overlap",
                }
            )
        if (
            is_full_slide_image(image, slide)
            and source_type in {"user-provided", "user-approved-rasterization"}
            and text_boxes
        ):
            violations.append(
                {
                    "field": "asset_provenance",
                    "path": path,
                    "reason": "full-slide raster background cannot be assembled with editable text",
                }
            )

    return violations


def quality_contract_violations(manifest):
    violations = []

    if "visual_inventory" not in manifest:
        violations.append(
            {
                "field": "visual_inventory",
                "reason": "page manifest must record the non-text visual inventory, even when it is empty",
            }
        )
    elif not isinstance(manifest.get("visual_inventory"), list):
        violations.append({"field": "visual_inventory", "reason": "visual_inventory must be a list"})

    background_strategy = manifest.get("background_strategy")
    if not background_strategy:
        violations.append(
            {
                "field": "background_strategy",
                "reason": "page manifest must record how the background was rebuilt or preserved",
            }
        )

    quality_checks = manifest.get("quality_checks")
    if not isinstance(quality_checks, dict):
        violations.append({"field": "quality_checks", "reason": "quality_checks must be an object"})
    else:
        for key in sorted(REQUIRED_QUALITY_CHECKS):
            if quality_checks.get(key) is not True:
                violations.append(
                    {
                        "field": f"quality_checks.{key}",
                        "reason": "required page QA check must be explicitly true",
                    }
                )

    visual_audit = manifest.get("visual_audit")
    if not isinstance(visual_audit, dict):
        violations.append({"field": "visual_audit", "reason": "visual_audit must be an object with source-versus-preview evidence"})
    else:
        if visual_audit.get("source_preview_compared") is not True:
            violations.append({"field": "visual_audit.source_preview_compared", "reason": "source.png and preview.png must be explicitly compared"})
        for kind in ("text_boxes", "arrows_connectors", "semantic_visuals"):
            expected = visual_audit.get(f"expected_{kind}")
            rebuilt = visual_audit.get(f"rebuilt_{kind}")
            if not isinstance(expected, int) or expected < 0 or not isinstance(rebuilt, int) or rebuilt < 0:
                violations.append({"field": f"visual_audit.{kind}", "reason": "expected and rebuilt counts must be nonnegative integers"})
            elif rebuilt != expected:
                violations.append({"field": f"visual_audit.{kind}", "reason": f"rebuilt count {rebuilt} does not match expected count {expected}"})
        for key in ("missing_object_ids", "misaligned_object_ids"):
            value = visual_audit.get(key)
            if not isinstance(value, list):
                violations.append({"field": f"visual_audit.{key}", "reason": "must be a list"})
            elif value:
                violations.append({"field": f"visual_audit.{key}", "reason": "visual audit contains unresolved objects", "objects": value})
        if not str(visual_audit.get("review_notes", "")).strip():
            violations.append({"field": "visual_audit.review_notes", "reason": "must record concrete comparison evidence"})
        if visual_audit.get("independent_review") is not True:
            violations.append({"field": "visual_audit.independent_review", "reason": "source-versus-preview review must be explicitly recorded as an independent pass"})

    visible_text_count = 0
    for index, item in enumerate(manifest.get("text_boxes", [])):
        text = str(item.get("text", ""))
        box = item.get("box_px")
        if not text.strip():
            violations.append({"field": f"text_boxes[{index}]", "reason": "empty placeholder text boxes are forbidden"})
            continue
        visible_text_count += 1
        if item.get("font_size_source") not in {"measured", "hints"}:
            violations.append({"field": f"text_boxes[{index}].font_size_source", "reason": "every visible text box must use measured or hint-derived font sizing"})
        if not isinstance(box, list) or len(box) != 4 or float(box[2]) < 2 or float(box[3]) < 2:
            violations.append({"field": f"text_boxes[{index}].box_px", "reason": "placeholder, off-canvas, or degenerate text boxes are forbidden"})
    if isinstance(visual_audit, dict) and isinstance(visual_audit.get("rebuilt_text_boxes"), int):
        if visual_audit["rebuilt_text_boxes"] != visible_text_count:
            violations.append({"field": "visual_audit.rebuilt_text_boxes", "reason": f"audit count does not match {visible_text_count} visible manifest text boxes"})

    connector_count = sum(1 for item in manifest.get("shapes", []) if item.get("type") in {"line", "path"})
    if isinstance(visual_audit, dict) and isinstance(visual_audit.get("rebuilt_arrows_connectors"), int):
        if visual_audit["rebuilt_arrows_connectors"] != connector_count:
            violations.append({"field": "visual_audit.rebuilt_arrows_connectors", "reason": f"audit count does not match {connector_count} line/path objects in the manifest"})

    for index, shape in enumerate(manifest.get("shapes", [])):
        for gradient_field in ("fill_gradient", "stroke_gradient"):
            violations.extend(
                {**violation, "field": f"shapes[{index}].{violation['field']}"}
                for violation in gradient_contract_violations(shape, gradient_field)
            )
        is_round_rect = shape.get("type") == "roundRect" or shape.get("preset") == "roundRect"
        if is_round_rect and not shape.get("source_corner_radius_px"):
            violations.append(
                {
                    "field": f"shapes[{index}]",
                    "reason": "roundRect requires source_corner_radius_px; use rect for source straight-corner containers",
                }
            )
        if is_round_rect and shape.get("source_corner_radius_px") and shape.get("box_px"):
            box = shape.get("box_px")
            radius = float(shape.get("source_corner_radius_px") or 0)
            min_dim = max(1.0, min(float(box[2]), float(box[3])))
            if radius > min_dim / 2:
                violations.append(
                    {
                        "field": f"shapes[{index}].source_corner_radius_px",
                        "reason": "roundRect source radius cannot exceed half of the smaller shape dimension",
                    }
                )

    for index, text_box in enumerate(manifest.get("text_boxes", [])):
        align = str(text_box.get("align", "left") or "left").strip().lower()
        if align not in TEXT_ALIGNMENTS:
            violations.append(
                {
                    "field": f"text_boxes[{index}].align",
                    "reason": "text align must be left, center, right, or the equivalent DrawingML token l, ctr, r",
                }
            )
        valign = str(text_box.get("valign", "top") or "top").strip().lower()
        if valign not in TEXT_VERTICAL_ALIGNMENTS:
            violations.append(
                {
                    "field": f"text_boxes[{index}].valign",
                    "reason": "text valign must be top, middle, bottom, or the equivalent DrawingML token t, ctr, b",
                }
            )

    violations.extend(foreground_asset_contract_violations(manifest))
    violations.extend(visual_inventory_contract_violations(manifest))
    return violations


def pixel_authoring_violations(manifest):
    violations = []
    source = manifest.get("source", {})
    if not source.get("width_px") or not source.get("height_px"):
        violations.append(
            {
                "field": "source.width_px/source.height_px",
                "reason": "page manifest must record the source image pixel size",
            }
        )

    for section in ("text_boxes", "images", "tables"):
        for index, item in enumerate(manifest.get(section, [])):
            if "box_px" not in item:
                violations.append(
                    {
                        "field": f"{section}[{index}].box_px",
                        "reason": "positioned text, image, and table objects must use source-image pixel coordinates",
                    }
                )

    for index, item in enumerate(manifest.get("shapes", [])):
        if item.get("type") == "line":
            if "points_px" not in item:
                violations.append(
                    {
                        "field": f"shapes[{index}].points_px",
                        "reason": "line shapes must use source-image pixel endpoints",
                    }
                )
        elif "box_px" not in item:
            violations.append(
                {
                    "field": f"shapes[{index}].box_px",
                    "reason": "positioned shapes must use source-image pixel coordinates",
                }
            )

    return violations


def normalize_for_validation(manifest):
    violations = pixel_authoring_violations(manifest)
    try:
        return normalize_manifest(manifest), violations
    except Exception as exc:
        violations.append({"field": "manifest", "reason": str(exc)})
        return manifest, violations


def line_geometry_violations(manifest, root):
    """Check actual slide objects, rather than trusting the page's QA flags."""
    if not any(item.get("type") == "path" or item.get("dash") or item.get("start_arrow") or item.get("end_arrow") or item.get("semantic_line_id")
               for item in manifest.get("shapes", [])):
        return []
    expected = ET.fromstring(slide_xml(normalize_manifest(manifest))).findall(".//p:sp", NS)
    actual = root.findall(".//p:sp", NS)
    if len(actual) != len(expected):
        return [{"field": "shapes", "reason": "slide object count differs from manifest; a line may be fragmented or missing"}]
    violations = []
    for index, (wanted, found) in enumerate(zip(expected, actual)):
        props = wanted.find("p:spPr", NS)
        name = wanted.find("p:nvSpPr/p:cNvPr", NS).get("name", "")
        if not name.startswith(("Path ", "Line ")) and not any(props.find(f"a:ln/a:{tag}", NS) is not None for tag in ("prstDash", "headEnd", "tailEnd")):
            continue
        # Whitespace and namespace prefix changes do not affect the structure.
        def structure(element):
            if element is None:
                return None
            return element.tag, sorted(element.attrib.items()), [structure(child) for child in element]

        if structure(props) != structure(found.find("p:spPr", NS)):
            violations.append({"field": f"slide.shapes[{index}]", "reason": "path geometry, position, dash or arrow properties differ from manifest"})
    return violations


def table_structure_violations(manifest, root):
    """Verify native table geometry, cells, merges and formatting in the actual PPTX."""
    def frames(slide):
        return [frame for frame in slide.findall(".//p:graphicFrame", NS)
                if frame.find("a:graphic/a:graphicData/a:tbl", NS) is not None]

    actual = frames(root)
    if len(actual) != len(manifest.get("tables", [])):
        return [{"field": "tables", "reason": "native table count differs from manifest"}]
    if not actual:
        return []
    expected = frames(ET.fromstring(slide_xml(normalize_manifest(manifest))))

    def structure(node):
        if node is None:
            return None
        return (node.tag, sorted(node.attrib.items()), node.text if node.tag == f"{{{NS['a']}}}t" else None,
                [structure(child) for child in node])

    violations = []
    for index, (wanted, found) in enumerate(zip(expected, actual)):
        for path in ("p:xfrm", "a:graphic"):
            if structure(wanted.find(path, NS)) != structure(found.find(path, NS)):
                violations.append({"field": f"tables[{index}]", "reason": "native table geometry, content, merges or style differs from manifest"})
                break
    return violations


def sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def flatten_required_text(value):
    """Return exact text strings that should be verified in the PPTX."""
    items = []
    if value is None:
        return items
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, dict):
        if "required_text" in value:
            return flatten_required_text(value.get("required_text"))
        if "items" in value:
            return flatten_required_text(value.get("items"))
        if "texts" in value:
            return flatten_required_text(value.get("texts"))
        if "text" in value:
            return flatten_required_text(value.get("text"))
        return items
    if isinstance(value, (list, tuple, set)):
        for item in value:
            items.extend(flatten_required_text(item))
    return items


def required_texts_from_manifest(manifest):
    required = []
    required.extend(flatten_required_text(manifest.get("required_text", [])))
    required.extend(flatten_required_text(manifest.get("text_inventory", [])))
    for table in manifest.get("tables", []):
        for text in flatten_required_text(table.get("cells", [])):
            required.extend(line for line in text.splitlines() if line)
    return required


def collect_text(xml_bytes):
    root = ET.fromstring(xml_bytes)
    # Runs within a paragraph are contiguous; paragraphs and explicit breaks
    # are not. Flattening every a:t erased source line breaks and joined labels.
    return "\n".join(
        "".join(
            "\n" if node.tag == f"{{{NS['a']}}}br" else node.text or ""
            for node in paragraph.iter()
            if node.tag in (f"{{{NS['a']}}}t", f"{{{NS['a']}}}br")
        )
        for paragraph in root.findall(".//a:p", NS)
    )


def collect_paragraph_text(xml_bytes):
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for paragraph in root.findall(".//a:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def collect_notes_texts(z, names):
    notes = {}
    for name in sorted(n for n in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)):
        match = re.search(r"notesSlide(\d+)\.xml$", name)
        if not match:
            continue
        notes[int(match.group(1))] = collect_paragraph_text(z.read(name))
    return notes


def validate_deck(args):
    deck_path = Path(args.deck_manifest).resolve()
    deck = read_manifest(deck_path)
    root = Path(deck.get("job_dir", deck_path.parent)).resolve()
    page_count = int(deck.get("page_count", len(deck.get("pages", []))))
    include_source = deck.get("include_source_slides", True) is True
    expected_pages = page_count * (2 if include_source else 1)
    notes_manifest = {}
    notes_path = deck.get("notes_manifest")
    if notes_path:
        notes_file = Path(notes_path)
        if not notes_file.is_absolute():
            notes_file = root / notes_file
        if notes_file.exists():
            notes_manifest = read_manifest(notes_file)

    report = {
        "pptx": str(Path(args.pptx).resolve()),
        "deck_manifest": str(deck_path),
        "expected_pages": expected_pages,
        "source_page_count": page_count,
        "slides": 0,
        "page_manifests_missing": [],
        "page_validation_missing": [],
        "failed_page_validations": [],
        "page_contract_violations": [],
        "source_slide_violations": [],
        "notes_expected": len(notes_manifest.get("notes", [])),
        "notes_found": 0,
        "notes_hash_mismatches": [],
        "missing_parts": [],
        "warnings": [],
        "passed": False,
    }

    geometry_manifests = []
    for page_index, page in enumerate(deck.get("pages", []), start=1):
        manifest_path = Path(page.get("manifest", ""))
        validation_path = Path(page.get("validation", ""))
        if not manifest_path.is_absolute():
            manifest_path = root / manifest_path
        if not validation_path.is_absolute():
            validation_path = root / validation_path
        if not manifest_path.exists():
            report["page_manifests_missing"].append(str(manifest_path))
        else:
            try:
                raw_manifest = read_manifest(manifest_path)
                normalized_manifest, authoring_violations = normalize_for_validation(raw_manifest)
                if not authoring_violations:
                    geometry_manifests.append((page_index, normalized_manifest))
                violations = (
                    authoring_violations
                    + page_contract_violations(normalized_manifest)
                    + quality_contract_violations(raw_manifest)
                )
                if violations:
                    report["page_contract_violations"].append(
                        {
                            "page_id": page.get("page_id"),
                            "manifest": str(manifest_path),
                            "violations": violations,
                        }
                    )
            except Exception as exc:
                report["page_contract_violations"].append(
                    {
                        "page_id": page.get("page_id"),
                        "manifest": str(manifest_path),
                        "violations": [{"field": "manifest", "reason": str(exc)}],
                    }
                )
        if not validation_path.exists():
            report["page_validation_missing"].append(str(validation_path))
        else:
            try:
                page_report = read_manifest(validation_path)
                if page_report.get("passed") is False:
                    report["failed_page_validations"].append(str(validation_path))
            except Exception as exc:
                report["failed_page_validations"].append(f"{validation_path}: {exc}")

    try:
        with zipfile.ZipFile(args.pptx) as z:
            names = z.namelist()
            report["slides"] = len([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)])
            presentation = ET.fromstring(z.read("ppt/presentation.xml"))
            slide_rels = {rel["id"]: rel["resolved"] for rel in relationship_targets(z, "ppt/_rels/presentation.xml.rels", names)}
            ordered_parts = [slide_rels.get(item.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
                             for item in presentation.findall("p:sldIdLst/p:sldId", NS)]
            if ordered_parts != [f"ppt/slides/slide{i}.xml" for i in range(1, expected_pages + 1)]:
                report["page_contract_violations"].append({"field": "slide_order", "reason": "presentation slide order/count differs from input order"})
            for page_index, page_manifest in geometry_manifests:
                slide_number = page_index * 2 if include_source else page_index
                slide_part = f"ppt/slides/slide{slide_number}.xml"
                if include_source:
                    source_path = root / deck["pages"][page_index - 1]["source_image"]
                    reference_part = f"ppt/slides/slide{slide_number - 1}.xml"
                    expected_reference = slide_xml(normalize_manifest(source_slide_manifest(page_manifest, source_path)))
                    reference_rels = relationship_targets(z, f"ppt/slides/_rels/slide{slide_number - 1}.xml.rels", names)
                    reference_images = [rel for rel in reference_rels if rel["type"].endswith("/image")]
                    if (reference_part not in names
                            or ET.canonicalize(z.read(reference_part).decode()) != ET.canonicalize(expected_reference)
                            or len(reference_images) != 1
                            or reference_images[0]["external"]
                            or reference_images[0]["resolved"] not in names
                            or hashlib.sha256(z.read(reference_images[0]["resolved"])).hexdigest() != file_sha256(source_path)):
                        report["source_slide_violations"].append({"page_index": page_index, "reason": "reference slide must contain the unchanged source raster in its content box"})
                if slide_part in names:
                    slide_root = ET.fromstring(z.read(slide_part))
                    violations = (line_geometry_violations(page_manifest, slide_root)
                                  + table_structure_violations(page_manifest, slide_root))
                    if violations:
                        report["page_contract_violations"].append({"page_index": page_index, "violations": violations})
            for part in ("[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"):
                if part not in names:
                    report["missing_parts"].append(part)
            notes_texts = collect_notes_texts(z, names)
            report["notes_found"] = len(notes_texts)
            for entry in notes_manifest.get("notes", []):
                page_index = int(entry.get("page_index", 0))
                if include_source:
                    page_index *= 2
                expected_hash = entry.get("text_sha256", sha256_text(entry.get("text", "")))
                actual = notes_texts.get(page_index)
                if actual is None:
                    report["notes_hash_mismatches"].append({"page_index": page_index, "reason": "missing notes slide"})
                elif sha256_text(actual) != expected_hash:
                    report["notes_hash_mismatches"].append({"page_index": page_index, "reason": "text hash mismatch"})
    except Exception as exc:
        report["warnings"].append(f"Unable to read pptx: {exc}")

    report["passed"] = (
        report["slides"] == expected_pages
        and not report["page_manifests_missing"]
        and not report["page_validation_missing"]
        and not report["failed_page_validations"]
        and not report["page_contract_violations"]
        and not report["source_slide_violations"]
        and not report["missing_parts"]
        and not report["notes_hash_mismatches"]
        and not report["warnings"]
    )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(0 if report["passed"] else 1)


def rel_source_part(rels_name):
    if not rels_name.endswith(".rels"):
        return posixpath.dirname(rels_name)
    directory = posixpath.dirname(rels_name)
    if directory.endswith("/_rels"):
        directory = posixpath.dirname(directory)
    source = posixpath.basename(rels_name)[:-5]
    return posixpath.normpath(posixpath.join(directory, source))


def resolve_target(rels_name, target):
    if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    source = rel_source_part(rels_name)
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def relationship_targets(z, rels_name, names):
    if rels_name not in names:
        return []
    root = ET.fromstring(z.read(rels_name))
    targets = []
    for rel in root.findall("rel:Relationship", NS):
        mode = rel.attrib.get("TargetMode")
        target = rel.attrib.get("Target")
        resolved = resolve_target(rels_name, target)
        targets.append(
            {
                "id": rel.attrib.get("Id"),
                "type": rel.attrib.get("Type", ""),
                "target": target,
                "resolved": resolved,
                "external": mode == "External",
            }
        )
    return targets


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx")
    parser.add_argument("--manifest")
    parser.add_argument("--deck-manifest")
    parser.add_argument("--required-text", action="append", default=[])
    parser.add_argument("--report")
    args = parser.parse_args()

    if args.deck_manifest:
        validate_deck(args)

    raw_manifest = read_manifest(args.manifest)
    manifest, authoring_violations = normalize_for_validation(raw_manifest)
    manifest_base = Path(args.manifest).resolve().parent if args.manifest else Path.cwd()
    required = list(args.required_text)
    required.extend(required_texts_from_manifest(manifest))

    report = {
        "pptx": str(Path(args.pptx).resolve()),
        "zip_ok": False,
        "slides": 0,
        "images": 0,
        "editable_text_shapes": 0,
        "native_tables": 0,
        "editable_table_cells": 0,
        "shape_count": 0,
        "all_text": "",
        "required_text": required,
        "missing_required_text": [],
        "missing_parts": [],
        "missing_relationship_targets": [],
        "missing_asset_provenance": [],
        "missing_manifest_images": [],
        "missing_provenance_sources": [],
        "invalid_asset_provenance": [],
        "media_hash_mismatches": [],
        "asset_provenance_checked": 0,
        "manifest_image_count": len(manifest.get("images", [])),
        "media_manifest_mismatch": False,
        "relationship_targets_checked": 0,
        "warnings": [],
        "page_contract_violations": [],
        "line_geometry_violations": [],
        "table_structure_violations": [],
    }

    try:
        with zipfile.ZipFile(args.pptx) as z:
            bad = z.testzip()
            report["zip_ok"] = bad is None
            if bad:
                report["warnings"].append(f"Bad zip member: {bad}")
            names = z.namelist()
            required_parts = [
                "[Content_Types].xml",
                "_rels/.rels",
                "ppt/presentation.xml",
                "ppt/_rels/presentation.xml.rels",
            ]
            for part in required_parts:
                if part not in names:
                    report["missing_parts"].append(part)
            slide_names = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
            report["slides"] = len(slide_names)
            report["images"] = len([n for n in names if n.startswith("ppt/media/")])
            report["media_manifest_mismatch"] = report["images"] != report["manifest_image_count"]
            for index, image in enumerate(manifest.get("images", []), start=1):
                image_path = image.get("path")
                if not image_path:
                    continue
                ext = Path(image_path).suffix.lower()
                if ext == ".jpeg":
                    ext = ".jpg"
                media_name = f"ppt/media/image{index}{ext}"
                source_path = Path(image_path)
                if not source_path.is_absolute():
                    source_path = manifest_base / source_path
                if media_name not in names:
                    report["media_hash_mismatches"].append(
                        {"path": image_path, "media": media_name, "reason": "missing media part"}
                    )
                    continue
                if source_path.exists():
                    manifest_hash = file_sha256(source_path)
                    media_hash = hashlib.sha256(z.read(media_name)).hexdigest()
                    if manifest_hash != media_hash:
                        report["media_hash_mismatches"].append(
                            {"path": image_path, "media": media_name, "reason": "hash mismatch"}
                        )
                else:
                    report["missing_manifest_images"].append(str(image_path))
            for slide_name in slide_names:
                rels_name = f"{posixpath.dirname(slide_name)}/_rels/{posixpath.basename(slide_name)}.rels"
                if rels_name not in names:
                    report["missing_parts"].append(rels_name)
            rel_files = [name for name in names if name.endswith(".rels")]
            for rels_name in rel_files:
                for target in relationship_targets(z, rels_name, names):
                    if target["external"] or not target["resolved"]:
                        continue
                    report["relationship_targets_checked"] += 1
                    if target["resolved"] not in names:
                        report["missing_relationship_targets"].append(
                            {
                                "rels": rels_name,
                                "id": target["id"],
                                "target": target["target"],
                                "resolved": target["resolved"],
                            }
                        )
            texts = []
            for slide_name in slide_names:
                xml = z.read(slide_name)
                root = ET.fromstring(xml)
                if not authoring_violations:
                    report["line_geometry_violations"].extend(line_geometry_violations(manifest, root))
                    report["table_structure_violations"].extend(table_structure_violations(manifest, root))
                tables = root.findall(".//a:tbl", NS)
                report["native_tables"] += len(tables)
                report["editable_table_cells"] += sum(
                    1 for table in tables for cell in table.findall("a:tr/a:tc", NS)
                    if cell.get("hMerge", "0") not in ("1", "true")
                    and cell.get("vMerge", "0") not in ("1", "true")
                    and any(node.text for node in cell.findall(".//a:t", NS))
                )
                shapes = root.findall(".//p:sp", NS)
                report["shape_count"] += len(shapes)
                report["editable_text_shapes"] += sum(1 for shape in shapes if shape.findall(".//a:t", NS))
                texts.append(collect_text(xml))
            report["all_text"] = "\n".join(texts)
    except Exception as exc:
        report["warnings"].append(f"Unable to read pptx: {exc}")

    for text in required:
        if text and text not in report["all_text"]:
            report["missing_required_text"].append(text)

    provenance = {}
    for entry in manifest.get("asset_provenance", []):
        path = entry.get("path")
        if path:
            provenance[Path(path).as_posix()] = entry

    for image in manifest.get("images", []):
        image_path = image.get("path")
        if not image_path:
            continue
        key = Path(image_path).as_posix()
        entry = provenance.get(key)
        if not entry:
            report["missing_asset_provenance"].append(key)
            continue
        report["asset_provenance_checked"] += 1
        source_type = entry.get("source_type")
        provenance_note = entry.get("provenance_note")
        if source_type not in ALLOWED_SOURCE_TYPES:
            report["invalid_asset_provenance"].append(
                {"path": key, "field": "source_type", "value": source_type}
            )
        if not provenance_note:
            report["invalid_asset_provenance"].append(
                {"path": key, "field": "provenance_note", "value": provenance_note}
            )
        if source_type == "user-approved-rasterization" and not entry.get("approval_note"):
            report["invalid_asset_provenance"].append(
                {"path": key, "field": "approval_note", "value": entry.get("approval_note")}
            )
        source = entry.get("source")
        if not source:
            report["missing_provenance_sources"].append({"path": key, "source": source})
            continue
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = manifest_base / source_path
        if not source_path.exists():
            report["missing_provenance_sources"].append({"path": key, "source": str(source)})
    report["page_contract_violations"] = (
        authoring_violations + page_contract_violations(manifest) + quality_contract_violations(raw_manifest)
    )

    report["passed"] = (
        report["zip_ok"]
        and report["slides"] >= 1
        and not report["media_manifest_mismatch"]
        and not report["missing_parts"]
        and not report["missing_relationship_targets"]
        and not report["media_hash_mismatches"]
        and not report["missing_required_text"]
        and not report["missing_asset_provenance"]
        and not report["missing_manifest_images"]
        and not report["missing_provenance_sources"]
        and not report["invalid_asset_provenance"]
        and not report["page_contract_violations"]
        and not report["line_geometry_violations"]
        and not report["table_structure_violations"]
        and (report["editable_text_shapes"] > 0 or report["editable_table_cells"] > 0 or not required)
    )

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
