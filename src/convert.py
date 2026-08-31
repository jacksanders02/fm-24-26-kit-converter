"""
This module exists to convert FM24 3D kits to the new format used by FM26

Original script provided by roundel0 on the Sortitoutsi forums:
https://sortitoutsi.net/content/74713/transferring-3d-outfits-from-fm24-to-fm26-in-photoshop?page=3#comment_854826
"""

from pathlib import Path
from tkinter import filedialog, messagebox
from os.path import abspath, dirname
import sys
from argparse import ArgumentParser
import logging
import numpy as np
from PIL import Image
import OpenEXR
from Imath import PixelType # False Positive -- pylint: disable=no-name-in-module

log = logging.getLogger(__name__)

# Path to script / executable (use for generating output dir)
SCRIPT_PATH = Path(abspath(dirname(sys.argv[0]))).resolve()

# Path to script / bundle directory (use for reading resources)
BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', abspath(dirname(__file__))))

LOOKUP_PATH = BUNDLE_DIR / "resources" / "fm24_to_fm26_lookup.exr"
OUT_DIR = SCRIPT_PATH / "output"

def debug_uv(uv: np.ndarray):
    """
    Log debug information about the uv map (log level = DEBUG)
    """
    u = uv[..., 0]
    v = uv[..., 1]
    log.debug("  U min/max: %.6f / %.6f", u.min(), u.max())
    log.debug("  V min/max: %.6f / %.6f", v.min(), v.max())

    h, w, _ = uv.shape
    sample_coords = [
        (0, 0),
        (h // 4, w // 4),
        (h // 2, w // 2),
        (3 * h // 4, 3 * w // 4),
        (h - 1, w - 1),
    ]
    log.debug("  Sample UVs at a few points:")
    for (yy, xx) in sample_coords:
        uu, vv = uv[yy, xx]
        log.debug("    (%4d, %4d) -> (%.6f, %.6f)", yy, xx, uu, vv)


def load_lookup_exr(path: Path) -> np.ndarray:
    """
    Load EXR lookup (R=U, G=V) into float32 array of shape (H, W, 2).

    This version:
      - ignores alpha completely
      - does NOT do any hole filling
      - log.debugs basic stats so we can see if the EXR actually has variation
    """
    log.info("Loading lookup EXR: %s", path)

    exr = OpenEXR.InputFile(str(path))
    dw = exr.header()["dataWindow"]

    dw_width  = dw.max.x - dw.min.x + 1
    dw_height = dw.max.y - dw.min.y + 1

    pixel_type = PixelType(PixelType.FLOAT)

    r = np.frombuffer(exr.channel("R", pixel_type), dtype=np.float32).reshape((dw_height, dw_width))
    g = np.frombuffer(exr.channel("G", pixel_type), dtype=np.float32).reshape((dw_height, dw_width))

    uv = np.stack([r, g], axis=-1)  # (H, W, 2)

    debug_uv(uv)

    return uv


def convert_image(src_path: Path, dest_path: Path, uv_map: np.ndarray):
    """Convert a single FM24 kit to FM26 using UV lookup."""
    log.info("Converting: %s", src_path)

    img = Image.open(src_path).convert("RGBA")
    src = np.array(img)

    # Lookup resolution (e.g., 1024x1024)
    h_u, w_u, _ = uv_map.shape
    h_s, w_s, _ = src.shape

    # ==============================
    # AUTO-RESIZE to lookup size
    # ==============================
    if (h_s, w_s) != (h_u, w_u):
        log.info("  - Resizing %dx%d → %dx%d", w_s, h_s, w_u, h_u)
        img = img.resize((w_u, h_u), Image.Resampling.BICUBIC)
        src = np.array(img)
        h_s, w_s, _ = src.shape

    # Compute sampling coordinates
    u = uv_map[..., 0]
    v = uv_map[..., 1]

    x = (u * (w_s - 1)).clip(0, w_s - 1)
    y = ((1.0 - v) * (h_s - 1)).clip(0, h_s - 1)
    out = src[np.rint(y).astype(np.int32), np.rint(x).astype(np.int32)]

    # Save
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, mode="RGBA").save(dest_path)

    log.info("  ✓ Saved to %s\n", dest_path)


def main():
    """
    Main entrypoint of the program,
    """
    parser = ArgumentParser("python convert.py")
    parser.add_argument(
        "-d", "--debug",
        help="toggle debug logging",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v", "--verbose",
        help="toggle verbose logging",
        action="store_const", dest="loglevel", const=logging.INFO,
        default=logging.WARNING,
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    if not LOOKUP_PATH.is_file():
        raise FileNotFoundError(f"Lookup EXR not found: {LOOKUP_PATH}")

    response = messagebox.askokcancel(
        "Select your FM24 Kits",
        "Choose a folder containing FM24 3D Kits\n\n"\
        '(folder picker will appear after you click "OK")'
    )
    if not response:
        sys.exit(0)

    src_dir = filedialog.askdirectory()
    if not src_dir:
        sys.exit(0)

    src_dir = Path(src_dir)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    uv_map = load_lookup_exr(LOOKUP_PATH)

    # Allowed formats
    exts = {".png"}
    files = [p for p in src_dir.rglob("*") if p.suffix.lower() in exts]

    log.debug("Found %d kits.\n", len(files))

    for f in files:
        rel = f.relative_to(src_dir)
        dst = OUT_DIR / rel
        try:
            convert_image(f, dst, uv_map)
        except Exception as e: # pylint: disable=broad-except
            log.debug(e)
            messagebox.showerror(
                "Error in Conversion!",
                f"Error converting kit {f}.\n\nPlease ensure all selected files are FM24 3D kits."
            )

    messagebox.showinfo(
        "Success!",
        f'All kits are converted.\n\nThe FM26 3D kits have been saved to {OUT_DIR}.'
    )


if __name__ == "__main__":
    main()
