#!/usr/bin/env python3
"""Export a presentation to PDF through a locally installed office renderer."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class PdfExportError(RuntimeError):
    """Raised when a presentation cannot be exported to a usable PDF."""


def _find_renderer(requested: str | None) -> str:
    candidates = [requested] if requested else ["soffice", "libreoffice"]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        resolved = str(path) if path.parent != Path(".") else shutil.which(candidate)
        if resolved and Path(resolved).is_file() and Path(resolved).stat().st_mode & 0o111:
            return str(Path(resolved).resolve())
    if requested:
        raise PdfExportError(f"PDF renderer is not executable or not found: {requested}")
    raise PdfExportError(
        "No PDF renderer found; install LibreOffice and ensure `soffice` or `libreoffice` is on PATH"
    )


def export_presentation_to_pdf(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    renderer: str | None = None,
    timeout: int = 120,
) -> dict[str, str | int]:
    """Convert *input_path* to PDF and return auditable artifact metadata.

    Conversion happens in a fresh temporary output directory and the generated
    PDF is moved into place only after the renderer exits successfully and the
    file has a valid PDF header. This prevents a stale output from being
    mistaken for the result of a failed conversion.
    """

    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise PdfExportError(f"Presentation does not exist or is not a file: {source}")
    if output_path is None:
        destination = source.with_suffix(".pdf")
    else:
        destination = Path(output_path).expanduser().resolve()
    if destination == source:
        raise PdfExportError("PDF output must be different from the presentation input")
    if destination.exists() and destination.is_dir():
        raise PdfExportError(f"PDF output path is a directory: {destination}")
    if timeout <= 0:
        raise PdfExportError("--timeout must be greater than zero")

    executable = _find_renderer(renderer)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".editppt-pdf-", dir=str(destination.parent)) as temp_root:
        temp_dir = Path(temp_root)
        output_dir = temp_dir / "output"
        profile_dir = temp_dir / "lo-profile"
        output_dir.mkdir()
        command = [
            executable,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(source),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfExportError(f"PDF conversion timed out after {timeout}s: {source}") from exc
        rendered = output_dir / f"{source.stem}.pdf"
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f"renderer exited with status {completed.returncode}"
            raise PdfExportError(f"PDF conversion failed for {source}: {detail}")
        if not rendered.is_file() or rendered.stat().st_size == 0:
            detail = stderr or stdout or "renderer produced no PDF"
            raise PdfExportError(f"PDF conversion produced no usable output for {source}: {detail}")
        with rendered.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise PdfExportError(f"PDF renderer produced an invalid file: {rendered}")
        rendered.replace(destination)

    return {
        "input": str(source),
        "output": str(destination),
        "renderer": executable,
        "bytes": destination.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a PowerPoint presentation to PDF.")
    parser.add_argument("input", metavar="PPTX", help="PowerPoint presentation to convert.")
    parser.add_argument("--out", metavar="PDF", help="Output PDF path. Defaults to the input basename with .pdf.")
    parser.add_argument("--renderer", metavar="PATH", help="LibreOffice/soffice executable (auto-detected by default).")
    parser.add_argument("--timeout", type=int, default=120, metavar="SECONDS", help="Renderer timeout (default: 120).")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result metadata.")
    args = parser.parse_args()
    try:
        result = export_presentation_to_pdf(
            args.input,
            args.out,
            renderer=args.renderer,
            timeout=args.timeout,
        )
    except PdfExportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PDF: {result['output']}")
        print(f"Renderer: {result['renderer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
