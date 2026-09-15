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
            "text_boxes": [{"id": "label", "text": "Editable label", "box_px": [30, 30, 220, 40],
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
            self.assertIn("Editable label", [item.text for item in slide.findall(".//a:t", ns)])
            self.assertTrue(slide.findall(".//a:tailEnd[@type='triangle']", ns))
        self.assertTrue((page / "preview.png").is_file())
        self.command("page", "contact-sheet", page)
        self.assertTrue((page / "split_assets_contact.png").is_file())
        # A buildable PPTX without source-grounded inventory/audit is not accepted.
        self.command("page", "validate", page, "--report", "validation.json", success=False)
        self.assertIs(json.loads((page / "validation.json").read_text())["passed"], False)


if __name__ == "__main__":
    unittest.main()
