#!/usr/bin/env python3
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
try:
    from tqdm import tqdm
except Exception:
    tqdm = None  # fallback: no progress bar


VALID_FORMATS = {"jpg", "jpeg", "png", "webp"}


def _validate_range(start: Optional[int], end: Optional[int], n_pages: int) -> Tuple[int, int]:
    # convert to 0-based inclusive indices
    first = 0 if not start else max(0, start - 1)
    last = n_pages - 1 if not end else min(n_pages - 1, end - 1)
    if first > last:
        raise ValueError(f"Invalid range: start={start}, end={end} for {n_pages} pages.")
    return first, last


def _ensure_outdir(pdf_path: Path, out_dir: Optional[Path]) -> Path:
    out = Path(out_dir) if out_dir else pdf_path.with_suffix("")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _maybe_grayscale(img: Image.Image, grayscale: bool) -> Image.Image:
    return img.convert("L") if grayscale else img


def _maybe_downscale(img: Image.Image, max_dim: Optional[int]) -> Image.Image:
    if max_dim and max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)  # in-place
    return img


def pdf_to_images(
    pdf_path: Path | str,
    out_dir: Optional[Path | str] = None,
    dpi: int = 200,
    quality: int = 90,
    start: Optional[int] = None,
    end: Optional[int] = None,
    fmt: str = "jpg",
    overwrite: bool = True,
    filename_template: str = "{stem}_p{page:03d}",
    password: Optional[str] = None,
    grayscale: bool = False,
    max_dim: Optional[int] = None,
) -> Path:
    """
    Convert each page of a PDF to images.

    Args:
        pdf_path: Path to input PDF.
        out_dir: Directory for output images. Defaults to <PDF name> (no suffix).
        dpi: Render resolution (72–600+). Higher = larger & sharper.
        quality: JPEG/WEBP quality (1–100). PNG ignores this.
        start, end: 1-based inclusive page range (e.g., start=2, end=5).
        fmt: Output format: 'jpg'/'jpeg', 'png', or 'webp'.
        overwrite: If False, skip existing files.
        filename_template: Python format string with {stem} and {page}.
        password: Password for encrypted PDFs.
        grayscale: Convert output to grayscale.
        max_dim: If set, downscale so max(width, height) == max_dim (preserves aspect).
    Returns:
        Path to the output directory.
    """
    fmt = fmt.lower()
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Unsupported format '{fmt}'. Choose from: {sorted(VALID_FORMATS)}.")

    dpi = int(dpi)
    if dpi <= 0:
        raise ValueError("dpi must be > 0.")
    if fmt in {"jpg", "webp"}:
        quality = int(quality)
        if not (1 <= quality <= 100):
            raise ValueError("quality must be in [1, 100].")

    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    out_dir = _ensure_outdir(pdf_path, Path(out_dir) if out_dir else None)

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    with fitz.open(pdf_path) as doc:
        if doc.needs_pass:
            if not password:
                raise PermissionError("PDF is encrypted. Provide --password.")
            if not doc.authenticate(password):
                raise PermissionError("Incorrect PDF password.")
        first, last = _validate_range(start, end, len(doc))

        iterator = range(first, last + 1)
        bar = tqdm(iterator, desc="Rendering pages", unit="page") if tqdm else iterator

        for i in bar:
            page = doc[i]
            pix = page.get_pixmap(matrix=mat, alpha=True)
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)

            if fmt in {"jpg", "webp"}:
                img = _flatten_to_rgb(img)
            img = _maybe_grayscale(img, grayscale)
            img = _maybe_downscale(img, max_dim)

            stem = pdf_path.stem
            out_base = filename_template.format(stem=stem, page=i + 1)
            out_file = out_dir / f"{out_base}.{fmt}"

            if out_file.exists() and not overwrite:
                continue

            save_kwargs = {}
            if fmt == "jpg":
                save_kwargs = dict(quality=quality, optimize=True, progressive=True)
                img.save(out_file, "JPEG", **save_kwargs)
            elif fmt == "png":
                # PNG ignores 'quality'; use optimize for size
                img.save(out_file, "PNG", optimize=True)
            elif fmt == "webp":
                save_kwargs = dict(quality=quality, method=6)
                img.save(out_file, "WEBP", **save_kwargs)
            else:
                # Shouldn't happen due to validation
                img.save(out_file)

    return out_dir


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert PDF pages to images using PyMuPDF + Pillow."
    )
    p.add_argument("pdf", help="Path to input PDF file.")
    p.add_argument("-o", "--out-dir", help="Output directory. Defaults to <PDF name> folder.")
    p.add_argument("--dpi", type=int, default=300, help="Render DPI (default: 300).")
    p.add_argument("--quality", type=int, default=92, help="Quality for JPG/WEBP [1-100] (default: 92).")
    p.add_argument("--start", type=int, help="Start page (1-based, inclusive).")
    p.add_argument("--end", type=int, help="End page (1-based, inclusive).")
    p.add_argument("--format", default="jpg", choices=sorted(VALID_FORMATS),
                   help="Output image format (default: jpg).")
    p.add_argument("--no-overwrite", action="store_true", help="Skip existing files instead of overwriting.")
    p.add_argument("--template", default="{stem}_p{page:03d}",
                   help="Filename template (default: '{stem}_p{page:03d}').")
    p.add_argument("--password", help="Password for encrypted PDFs.")
    p.add_argument("--grayscale", action="store_true", help="Convert outputs to grayscale.")
    p.add_argument("--max-dim", type=int, help="Downscale so max dimension equals this value (px).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    try:
        out = pdf_to_images(
            pdf_path=args.pdf,
            out_dir=args.out_dir,
            dpi=args.dpi,
            quality=args.quality,
            start=args.start,
            end=args.end,
            fmt=args.format,
            overwrite=not args.no_overwrite,
            filename_template=args.template,
            password=args.password,
            grayscale=args.grayscale,
            max_dim=args.max_dim,
        )
        print(f"Saved images to: {out}")
        return 0
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
