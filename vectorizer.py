import os, shutil, subprocess, tempfile, time
import numpy as np, cv2
from PIL import Image
from typing import Tuple

# ----------------- Helpers -----------------
def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def _run(cmd):
    return subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ).stdout

def _median_bg_from_corners(rgb: np.ndarray) -> np.ndarray:
    corners = np.vstack([rgb[0,0], rgb[0,-1], rgb[-1,0], rgb[-1,-1]])
    return np.median(corners, axis=0).astype(np.float32)

def _remove_small_components(mask: np.ndarray, min_area_px: int) -> np.ndarray:
    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8), connectivity=8
    )
    keep = np.zeros_like(mask, dtype=np.uint8)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_area_px:
            keep[labels == i] = 255
    return keep

# ----------------- Mask generation -----------------
def _smart_mask(img_rgba: np.ndarray, report=lambda *_: None):
    """
    Produce a mask where 255 = logo (foreground), 0 = background.
    If no alpha channel: separate background/foreground with k-means (k=2).
    Then denoise and remove tiny components.
    """
    h, w = img_rgba.shape[:2]
    alpha = img_rgba[..., 3]
    rgb   = img_rgba[..., :3].astype(np.float32)

    if alpha.min() == 255 and alpha.max() == 255:
        report("• No alpha: using k-means (k=2) to segment background/foreground…")
        Z = rgb.reshape(-1, 3)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
        _, labels, _ = cv2.kmeans(Z, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        labels = labels.reshape(h, w)
        # assume the largest cluster is background
        cnt0, cnt1 = np.count_nonzero(labels == 0), np.count_nonzero(labels == 1)
        bg_lab = 0 if cnt0 >= cnt1 else 1
        fg_lab = 1 - bg_lab
        mask_fg = np.where(labels == fg_lab, 255, 0).astype(np.uint8)
    else:
        report("• Alpha present: alpha>10 → foreground…")
        mask_fg = (alpha > 10).astype(np.uint8) * 255

    report("• Denoising & removing small components…")
    mask_fg = cv2.medianBlur(mask_fg, 3)
    min_area = max(16, int(0.0002 * w * h))  # drop anything smaller than ~0.02% of image
    mask_fg = _remove_small_components(mask_fg, min_area)
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), 1)

    # clear a thin frame to avoid leftover border hairlines in the SVG
    b = 2  # border thickness in px
    mask_fg[:b, :] = 0
    mask_fg[-b:, :] = 0
    mask_fg[:, :b] = 0
    mask_fg[:, -b:] = 0

    # Potrace traces BLACK as foreground; we invert PBM so 0=black=foreground
    invert_for_potrace = True
    return mask_fg, invert_for_potrace

def _make_pbm(mask_fg: np.ndarray, scale_up: int = 6, invert_for_potrace: bool = True) -> str:
    h, w = mask_fg.shape
    big = cv2.resize(mask_fg, (w * scale_up, h * scale_up), interpolation=cv2.INTER_NEAREST)
    if invert_for_potrace:
        big = 255 - big  # 0 = black = foreground (for potrace)

    # Use a secure NamedTemporaryFile to avoid race conditions
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pbm") as tmp:
        pbm_path = tmp.name
    Image.fromarray(big).convert("1").save(pbm_path)  # 1-bit PBM
    return pbm_path

# ----------------- Main vectorization -----------------
def vectorize_image(
    input_path: str,
    output_svg_path: str,
    report=lambda *_: None,
    fill_color: str = "#C59A52",
    scale_up: int = 6,
    alphamax: float = 1.2,
    opttolerance: float = 0.2,
    turdsize: int = 2,
    turnpolicy: str = "minority",
):
    """
    Bitmap → SVG (Potrace-based, detail-preserving).
    Ideal for single-color logos on transparent background.
    """
    if not _which("potrace"):
        raise RuntimeError("potrace not found. Install:  brew install potrace")

    report("🧭 Loading image…", 12); time.sleep(0.1)
    im = Image.open(input_path).convert("RGBA")
    arr = np.array(im)

    report("🔎 Generating smart mask…", 26); time.sleep(0.15)
    mask_fg, inv = _smart_mask(arr, report=report)
    try:
        coverage = (mask_fg.mean() / 255.0) * 100.0
        report(f"• Mask coverage: {coverage:.1f}%", 32)
    except Exception:
        pass

    report("🗂️ Preparing PBM…", 40); time.sleep(0.1)
    pbm = _make_pbm(mask_fg, scale_up=scale_up, invert_for_potrace=inv)
    try:
        report(f"• PBM size: {im.width*scale_up}×{im.height*scale_up}px", 41)
    except Exception:
        pass

    report("✒️ Tracing with Potrace…", 65)
    cmd = [
        "potrace", pbm,
        "-s", "-o", output_svg_path,
        "-C", fill_color,
        "-a", str(alphamax),
        "-O", str(opttolerance),
        "-t", str(turdsize),
        "--longcurve",
        "-z", turnpolicy,  # turnpolicy: black/white/left/right/minority/majority
    ]
    # Stream progress while potrace runs (65 → 74)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tick = 0
    while proc.poll() is None:
        time.sleep(0.5)
        tick += 1
        pct = min(74, 65 + tick)
        report("• Building Bézier curves…", pct)
    out = proc.stdout.read() if proc.stdout else ""
    if proc.returncode != 0:
        report(f"Potrace error: {out}", 74)
        raise RuntimeError(f"Potrace failed: {out}")

    try: os.remove(pbm)
    except: pass

    report("✅ SVG ready.", 75); time.sleep(0.05)
    return output_svg_path

# ----------------- Exports -----------------
def svg_to_png(svg_path: str, out_path: str, dpi: int = 300,
               width_px=None, height_px=None, report=lambda *_: None) -> bool:
    """
    Preference: inkscape → rsvg-convert → cairosvg.
    - If width_px/height_px is provided, use pixel target (sharpest).
    - Otherwise use dpi.
    - Keep transparent background and crop to drawing area.
    Streams progress during export (86 → 92).
    """
    try:
        report("🖼️ PNG export starting…", 82)
        import time as _t, subprocess as _sp

        # INKSCAPE
        if _which("inkscape"):
            report("• Tool: Inkscape found.", 83)
            report("• Settings: transparent background + crop to drawing.", 84)
            cmd = ["inkscape", svg_path, "--export-type=png",
                   "--export-background-opacity=0",
                   "--export-area-drawing",
                   f"--export-filename={out_path}"]
            if width_px:
                report(f"• Target width: {int(width_px)} px", 85)
                cmd += [f"--export-width={int(width_px)}"]
                if height_px:
                    cmd += [f"--export-height={int(height_px)}"]
            else:
                report(f"• DPI: {int(dpi)}", 85)
                cmd += [f"--export-dpi={int(dpi)}"]
            report("• Launching export…", 86)
            proc = _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True)
            tick = 0
            while proc.poll() is None:
                _t.sleep(0.5)
                tick += 1
                report("• Rendering PNG…", min(91, 86 + tick))
            out = proc.stdout.read() if proc.stdout else ""
            if proc.returncode != 0:
                report(f"PNG error (Inkscape): {out}", 92)
                return False
            report("• Render complete. File written.", 92)
            return True

        # RSVG-CONVERT
        if _which("rsvg-convert"):
            report("• Tool: rsvg-convert found.", 83)
            cmd = ["rsvg-convert", "-f", "png", "-o", out_path]
            if width_px:
                report(f"• Target width: {int(width_px)} px", 85)
                cmd += ["-w", str(int(width_px))]
            if height_px:
                cmd += ["-h", str(int(height_px))]
            if not width_px and not height_px:
                report(f"• DPI (simulated): {int(dpi)} (tool prefers px)", 85)
            cmd += [svg_path]
            report("• Launching export…", 86)
            proc = _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True)
            tick = 0
            while proc.poll() is None:
                _t.sleep(0.5)
                tick += 1
                report("• Rendering PNG…", min(91, 86 + tick))
            out = proc.stdout.read() if proc.stdout else ""
            if proc.returncode != 0:
                report(f"PNG error (rsvg-convert): {out}", 92)
                return False
            report("• Render complete. File written.", 92)
            return True

        # CAIROSVG (fallback)
        try:
            report("• Tool: cairosvg (fallback).", 83)
            import cairosvg
            kwargs = {"url": svg_path, "write_to": out_path}
            if width_px:
                report(f"• Target width: {int(width_px)} px", 85)
                kwargs["output_width"] = int(width_px)
            if height_px:
                kwargs["output_height"] = int(height_px)
            if dpi:
                kwargs["dpi"] = int(dpi)
            report("• Launching export…", 86)
            # simulate progress while blocking
            for i in range(4):
                _t.sleep(0.4)
                report("• Rendering PNG…", min(91, 86 + i))
            cairosvg.svg2png(**kwargs)
            report("• Render complete. File written.", 92)
            return True
        except Exception as e:
            report(f"PNG converter not available: {e}", 92)
            return False
    except Exception as e:
        report(f"PNG error: {e}", 92)
        return False

def svg_to_pdf(svg_path: str, out_path: str, report=lambda *_: None) -> bool:
    try:
        report("📄 PDF export starting…", 94)
        if _which("inkscape"):
            report("• Tool: Inkscape found.", 95)
            report("• Settings: crop to drawing area.", 96)
            _run(["inkscape", svg_path, "--export-type=pdf", "--export-area-drawing",
                  f"--export-filename={out_path}"])
            report("• PDF written.", 98)
            return True
        if _which("rsvg-convert"):
            report("• Tool: rsvg-convert found.", 95)
            _run(["rsvg-convert", "-f", "pdf", "-o", out_path, svg_path])
            report("• PDF written.", 98)
            return True
        try:
            report("• Tool: cairosvg (fallback).", 95)
            import cairosvg
            cairosvg.svg2pdf(url=svg_path, write_to=out_path)
            report("• PDF written.", 98)
            return True
        except Exception as e:
            report(f"PDF converter not available: {e}", 98)
            return False
    except Exception as e:
        report(f"PDF error: {e}", 98)
        return False