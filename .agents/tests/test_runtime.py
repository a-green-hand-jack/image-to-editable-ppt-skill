"""Offline regression checks for the packaged CLI and skill resources."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import editppt
from PIL import Image


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="editppt-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = os.environ.copy()
        # Exercise the imported package even from an unpacked wheel, outside the repo.
        self.env["PYTHONPATH"] = str(Path(editppt.__file__).resolve().parent.parent)
        self.env["EDITPPT_CONFIG_HOME"] = str(self.root / "config")
        self.env["CODEX_AUTH_FILE"] = str(self.root / "no-auth.json")
        self.env["CODEX_PPT_HOME"] = str(self.root / "no-legacy-config")
        for name in ("PADDLE_OCR_TOKEN", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
            self.env.pop(name, None)
        self.source = self.root / "source input.png"
        Image.new("RGB", (480, 240), "white").save(self.source)
        self.run = self.root / "run with spaces"

    def command(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, "-m", "editppt.cli", *map(str, args)],
            cwd=self.root, env=self.env, text=True, capture_output=True, timeout=60,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def prepare(self):
        self.command("prepare", self.source, "--job-dir", self.run)
        return self.run / "pages" / "page_001"

    @unittest.skipUnless(os.getenv("EDITPPT_TEST_LATEX_ENGINE"), "Set EDITPPT_TEST_LATEX_ENGINE to a working host executable")
    def test_display_formula_compiles_in_standalone(self):
        output = self.root / "display-formula.pdf"
        self.command("formula", "render-latex", "--engine", os.environ["EDITPPT_TEST_LATEX_ENGINE"],
                     "--tex", r"\begin{aligned}I_1&=\frac{a}{b}\\M&=\sum_{i=1}^{n}x_i\end{aligned}",
                     "--out", output, "--format", "pdf")
        self.assertTrue(output.read_bytes().startswith(b"%PDF-"))

    def test_export_pdf_validates_renderer_output(self):
        presentation = self.root / "figure.pptx"
        presentation.write_bytes(b"synthetic presentation")
        renderer = self.root / "fake-soffice"
        renderer.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "import sys\n"
            "out = Path(sys.argv[sys.argv.index('--outdir') + 1])\n"
            "source = Path(sys.argv[-1])\n"
            "(out / (source.stem + '.pdf')).write_bytes(b'%PDF-1.7\\nsynthetic')\n",
            encoding="utf-8",
        )
        renderer.chmod(0o755)
        output = self.root / "paper" / "figure.pdf"
        result = self.command("export-pdf", presentation, "--out", output,
                              "--renderer", renderer, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(Path(payload["output"]), output.resolve())
        self.assertEqual(Path(payload["renderer"]), renderer.resolve())
        self.assertEqual(output.read_bytes(), b"%PDF-1.7\nsynthetic")

    def test_prepare_packaged_prompt_and_local_claim(self):
        page = self.prepare()
        hints = json.loads((page / "text_hints.json").read_text())
        self.assertEqual(hints["backend"], "builtin-ink")
        state = json.loads(self.command("run", "next", self.run, "--json").stdout)
        self.assertEqual(state["stage"], "rebuild_page_locally")
        skill = Path(editppt.__file__).parent / "skills" / "image-to-editable-ppt"
        prompt = page / "worker-prompt.md"
        result = subprocess.run(
            [sys.executable, str(skill / "scripts" / "build-page-worker-prompt.py"),
             str(self.run), "--page", "1", "--out", str(prompt)],
            cwd=self.root, env=self.env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(str(page), prompt.read_text())
        self.assertNotIn("{{SKILL_ROOT}}", prompt.read_text())
        self.assertTrue((skill / "references" / "render-validation.md").is_file())
        self.command("run", "dispatch", self.run, "--page", "1", "--agent-id", "main",
                     "--prompt-file", prompt, "--local")
        state = json.loads(self.command("run", "next", self.run, "--json").stdout)
        self.assertEqual(state["stage"], "wait")

    def test_native_build_and_reject_missing_acceptance_evidence(self):
        page = self.prepare()
        request = json.loads((page / "page_request.json").read_text())
        manifest = {
            "source": {"path": "source.png", "width_px": 480, "height_px": 240},
            "slide": request["slide"], "content_box": request["content_box"],
            "required_text": ["Editable\nlabel"],
            "text_boxes": [{"id": "label", "text": "Editable\nlabel", "box_px": [30, 30, 220, 70],
                            "font_size": 18, "font": "Arial", "fit_text": False}],
            "shapes": [{"id": "arrow", "type": "line", "points_px": [40, 130, 400, 130],
                        "stroke": "000000", "end_arrow": "triangle"}],
        }
        (page / "manifest.json").write_text(json.dumps(manifest))
        self.command("page", "build", page)
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        with zipfile.ZipFile(page / "page.pptx") as archive:
            self.assertIsNone(archive.testzip())
            slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
            self.assertEqual([item.text for item in slide.findall(".//a:t", ns)], ["Editable", "label"])
            self.assertTrue(slide.findall(".//a:tailEnd[@type='triangle']", ns))
        self.assertTrue((page / "preview.png").is_file())
        self.command("page", "contact-sheet", page)
        self.assertTrue((page / "split_assets_contact.png").is_file())
        # A buildable PPTX without source-grounded inventory/audit is not accepted.
        self.command("page", "validate", page, "--report", "validation.json", success=False)
        validation = json.loads((page / "validation.json").read_text())
        self.assertIs(validation["passed"], False)
        self.assertEqual(validation["missing_required_text"], [])
        self.assertIn("Editable\nlabel", validation["all_text"])

    def test_final_deck_pairs_sources_with_editable_pages_and_notes(self):
        other = self.root / "portrait.png"
        Image.new("RGB", (240, 480), "blue").save(other)
        self.command("prepare", self.source, other, "--job-dir", self.run, "--no-text-hints")
        # Fixture notes exercise the source-page to final-slide mapping.
        (self.run / "notes_manifest.json").write_text(json.dumps({"notes": [
            {"page_index": 1, "text": "First note"},
            {"page_index": 2, "text": "Second note"},
        ]}))
        for index, size in enumerate(((480, 240), (240, 480)), start=1):
            page = self.run / "pages" / f"page_{index:03d}"
            request = json.loads((page / "page_request.json").read_text())
            manifest = {
                "source": {"width_px": size[0], "height_px": size[1]},
                "slide": request["slide"], "content_box": request["content_box"],
                "text_boxes": [{"id": "label", "text": f"Page {index}", "box_px": [20, 20, 150, 35],
                                "font_size": 12, "font_size_source": "measured"}],
                "visual_inventory": [], "background_strategy": "native solid fill fixture",
                "quality_checks": dict.fromkeys(("font_size_calibrated", "visual_inventory_matched",
                                                  "background_strategy_checked", "shape_corner_geometry_checked"), True),
                "visual_audit": {"source_preview_compared": True, "independent_review": True,
                                 "source_visual_object_ids": [], "missing_object_ids": [], "misaligned_object_ids": [],
                                 "expected_text_boxes": 1, "rebuilt_text_boxes": 1,
                                 "expected_arrows_connectors": 0, "rebuilt_arrows_connectors": 0,
                                 "expected_semantic_visuals": 0, "rebuilt_semantic_visuals": 0,
                                 "review_notes": "Synthetic structural fixture, not visual acceptance evidence."},
            }
            (page / "manifest.json").write_text(json.dumps(manifest))
            prompt = page / "worker-prompt.md"
            prompt.write_text("Synthetic fixture worker")
            self.command("run", "dispatch", self.run, "--page", index, "--agent-id", f"fixture-{index}",
                         "--prompt-file", prompt)
            self.command("page", "build", page)
            self.command("page", "contact-sheet", page)
            self.command("page", "validate", page, "--report", "validation.json")
            (page / "page_result.json").write_text("{}")
            self.command("run", "record", self.run, "--page", index, "--agent-id", f"fixture-{index}")
        self.command("run", "finalize", self.run)
        deck = json.loads((self.run / "deck_manifest.json").read_text())
        final = self.run / deck["output"]
        report = json.loads((final.parent / "validation.json").read_text())
        self.assertTrue(report["passed"])
        self.assertEqual(report["slides"], 4)
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
              "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
        with zipfile.ZipFile(final) as archive:
            for index in (1, 2):
                reference = ET.fromstring(archive.read(f"ppt/slides/slide{index * 2 - 1}.xml"))
                editable = ET.fromstring(archive.read(f"ppt/slides/slide{index * 2}.xml"))
                self.assertEqual(len(reference.findall(".//p:pic", ns)), 1)
                self.assertEqual(reference.findall(".//a:t", ns), [])
                self.assertEqual([node.text for node in editable.findall(".//a:t", ns)], [f"Page {index}"])
                self.assertEqual(archive.read(f"ppt/media/image{index}.png"),
                                 (self.run / "pages" / f"page_{index:03d}" / "source.png").read_bytes())
            self.assertIn(b"First note", archive.read("ppt/notesSlides/notesSlide2.xml"))
            self.assertIn(b"Second note", archive.read("ppt/notesSlides/notesSlide4.xml"))
            parts = {name: archive.read(name) for name in archive.namelist()}
        # A valid ZIP with the wrong reference image must fail deck validation.
        parts["ppt/media/image1.png"] = parts["ppt/media/image2.png"]
        with zipfile.ZipFile(final, "w") as archive:
            for name, data in parts.items():
                archive.writestr(name, data)
        validator = Path(editppt.__file__).parent / "runtime" / "validate_pptx.py"
        result = subprocess.run([sys.executable, str(validator), str(final), "--deck-manifest",
                                 str(self.run / "deck_manifest.json")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["source_slide_violations"])


if __name__ == "__main__":
    unittest.main()
