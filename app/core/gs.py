"""
gs.py  –  Ghostscript discovery and EPS/AI → image conversion.

The crop bug fix:
  EPS files  →  -dEPSCrop   (reads %%BoundingBox from PostScript header)
  AI / PDF   →  NO crop flag (full page MediaBox = what Illustrator exports)
  -dUseCropBox was wrong for AI: the CropBox is often a tiny thumbnail region.
"""

import glob
import os
import shutil
import subprocess
import sys


# ── Discovery ────────────────────────────────────────────────────────────────

def find() -> str | None:
    """Return the path to gswin64c / gswin32c / gs, or None if not found."""
    env = os.environ.get("GS_EXE")
    if env and os.path.isfile(env):
        return env

    # Bundled next to this executable (portable distribution).
    here = os.path.dirname(
        os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    )
    for sub in ("gs", "bin", ""):
        for exe in ("gswin64c.exe", "gswin32c.exe", "gs.exe"):
            cand = os.path.join(here, sub, exe) if sub else os.path.join(here, exe)
            if os.path.isfile(cand):
                return cand

    # On PATH.
    for name in (["gswin64c.exe", "gswin32c.exe", "gs.exe"] if os.name == "nt" else ["gs"]):
        found = shutil.which(name)
        if found:
            return found

    # Standard Program Files install.
    if os.name == "nt":
        for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(var)
            if not base:
                continue
            for exe in ("gswin64c.exe", "gswin32c.exe"):
                for p in glob.glob(os.path.join(base, "gs", "gs*", "bin", exe)):
                    if os.path.isfile(p):
                        return p
    return None


def get_version(gs_exe: str) -> str:
    try:
        r = subprocess.run(
            [gs_exe, "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=_nw(),
        )
        return r.stdout.strip()
    except Exception:
        return "?"


def _nw() -> int:
    return 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW


# ── File-type detection ───────────────────────────────────────────────────────

def is_eps(path: str) -> bool:
    """True for genuine EPS/PostScript, False for PDF-based AI."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        # PostScript text header OR binary EPS magic bytes
        return header[:4] in (b"%!PS", b"\xc5\xd0\xd3\xc6")
    except Exception:
        return False


# ── Conversion ────────────────────────────────────────────────────────────────

def convert(
    gs_exe:     str,
    src:        str,
    dst_base:   str,   # destination path WITHOUT extension
    fmt:        str,   # "png" or "jpg"
    dpi:        int,
    jpg_quality: int,
    all_pages:  bool,
    bg_white:   bool,
) -> list[str]:
    """
    Rasterise one EPS or AI file.
    Returns the list of output image paths actually written.
    Originals are never modified.
    """
    ext = "png" if fmt == "png" else "jpg"
    dst_dir = os.path.dirname(dst_base) or "."
    tmp_dir = os.path.join(dst_dir, ".~tmp_conv")
    os.makedirs(tmp_dir, exist_ok=True)
    pattern = os.path.join(tmp_dir, f"p_%d.{ext}")

    try:
        device = ("png16m" if bg_white else "pngalpha") if fmt == "png" else "jpeg"
        cmd = [
            gs_exe,
            "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dNOPROMPT",
            "-dTextAlphaBits=4",     # maximum anti-aliasing
            "-dGraphicsAlphaBits=4",
            "-dMaxBitmap=2000000000",
            f"-sDEVICE={device}",
            f"-r{dpi}",
            f"-sOutputFile={pattern}",
        ]

        if is_eps(src):
            # EPS: use the %%BoundingBox in the PostScript header (= artboard size)
            cmd.append("-dEPSCrop")
        # AI/PDF: no crop flag → use full MediaBox (= Illustrator artboard)

        if not all_pages:
            cmd += ["-dFirstPage=1", "-dLastPage=1"]

        if fmt == "jpg":
            cmd.append(f"-dJPEGQ={jpg_quality}")

        cmd.append(src)

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=_nw(),
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "Ghostscript error").strip()[:400])

        # Collect rendered pages in order.
        pages: list[tuple[int, str]] = []
        for fn in os.listdir(tmp_dir):
            if fn.startswith("p_") and fn.endswith("." + ext):
                try:
                    idx = int(fn[2: -len(ext) - 1])
                except ValueError:
                    idx = 99999
                pages.append((idx, os.path.join(tmp_dir, fn)))
        pages.sort()

        if not pages:
            raise RuntimeError("Ghostscript produced no output image.")

        outputs: list[str] = []
        for i, (_, tmp_path) in enumerate(pages, start=1):
            page_suffix = "" if (len(pages) == 1) else ("" if i == 1 else f"_{i}")
            final = dst_base + page_suffix + "." + ext
            _move(tmp_path, final)
            outputs.append(final)
        return outputs

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _move(src: str, dst: str) -> None:
    if os.path.abspath(src) == os.path.abspath(dst):
        return
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)
