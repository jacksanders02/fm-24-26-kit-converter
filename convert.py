from pathlib import Path
import numpy as np
from PIL import Image
from tkinter import filedialog, messagebox
import OpenEXR, Imath   # pip install OpenEXR Imath
from os.path import abspath
from sys import argv
from argparse import ArgumentParser
import logging

log = logging.getLogger(__name__)

SCRIPT_PATH = Path(abspath(argv[0])).resolve().parent
# ============================================================
# EDIT THESE THREE PATHS
# ============================================================
LOOKUP_PATH = SCRIPT_PATH / "fm24_to_fm26_lookup.exr"
OUT_DIR    = SCRIPT_PATH / "output"
# ============================================================


def load_lookup_exr(path: Path) -> np.ndarray:
    """
    Load EXR lookup (R=U, G=V) into float32 array of shape (H, W, 2).

    This version:
      - ignores alpha completely
      - does NOT do any hole filling
      - log.debugs basic stats so we can see if the EXR actually has variation
    """
    log.info(f"Loading lookup EXR: {path}")

    exr = OpenEXR.InputFile(str(path))
    header = exr.header()
    dw = header["dataWindow"]

    width  = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1

    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)

    r = np.frombuffer(exr.channel("R", FLOAT), dtype=np.float32).reshape((height, width))
    g = np.frombuffer(exr.channel("G", FLOAT), dtype=np.float32).reshape((height, width))

    uv = np.stack([r, g], axis=-1)  # (H, W, 2)

    # ---- Debug: log.debug some stats so we can see if UVs vary ----
    u = uv[..., 0]
    v = uv[..., 1]
    log.debug(f"  U min/max: {u.min():.6f} / {u.max():.6f}")
    log.debug(f"  V min/max: {v.min():.6f} / {v.max():.6f}")

    # sample a few points across the image just to see if they differ
    H, W, _ = uv.shape
    sample_coords = [
        (0, 0),
        (H // 4, W // 4),
        (H // 2, W // 2),
        (3 * H // 4, 3 * W // 4),
        (H - 1, W - 1),
    ]
    log.debug("  Sample UVs at a few points:")
    for (yy, xx) in sample_coords:
        uu, vv = uv[yy, xx]
        log.debug(f"    ({yy:4d}, {xx:4d}) -> ({uu:.6f}, {vv:.6f})")

    return uv


def convert_image(src_path: Path, OUT_DIR: Path, uv_map: np.ndarray):
    """Convert a single FM24 kit to FM26 using UV lookup."""
    log.info(f"Converting: {src_path}")

    img = Image.open(src_path).convert("RGBA")
    src = np.array(img)

    # Lookup resolution (e.g., 1024x1024)
    Hu, Wu, _ = uv_map.shape
    Hs, Ws, _ = src.shape

    # ==============================
    # AUTO-RESIZE to lookup size
    # ==============================
    if (Hs, Ws) != (Hu, Wu):
        log.info(f"  - Resizing {Ws}x{Hs} → {Wu}x{Hu}")
        img = img.resize((Wu, Hu), Image.BICUBIC)
        src = np.array(img)
        Hs, Ws, _ = src.shape

    # Compute sampling coordinates
    u = uv_map[..., 0]
    v = uv_map[..., 1]

    X = (u * (Ws - 1)).clip(0, Ws - 1)
    Y = ((1.0 - v) * (Hs - 1)).clip(0, Hs - 1)

    xi = np.rint(X).astype(np.int32)
    yi = np.rint(Y).astype(np.int32)

    out = src[yi, xi]

    # Save
    OUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, mode="RGBA").save(OUT_DIR)

    log.info(f"  ✓ Saved to {OUT_DIR}\n")


def main():
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

    messagebox.showinfo("Select your FM24 Kits", 'Choose a folder containing FM24 3D Kits\n\n(folder picker will appear after you click "Ok")')
    src_dir = Path(filedialog.askdirectory())

    if not LOOKUP_PATH.is_file():
        raise FileNotFoundError(f"Lookup EXR not found: {LOOKUP_PATH}")
    if not src_dir.is_dir():
        raise NotADirectoryError(f"FM24 directory not found: {src_dir}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    uv_map = load_lookup_exr(LOOKUP_PATH)

    # Allowed formats
    exts = {".png"}
    files = [p for p in src_dir.rglob("*") if p.suffix.lower() in exts]

    log.debug(f"Found {len(files)} kits.\n")

    for f in files:
        rel = f.relative_to(src_dir)
        dst = OUT_DIR / rel
        try:
            convert_image(f, dst, uv_map)
        except Exception as e:
            messagebox.showerror("Error in Conversion!", f"Error converting kit {f}.\n\nPlease ensure all selected files are FM24 3D kits.")

    messagebox.showinfo("Success!", 'All kits are converted.\n\nThe FM26 3D kits should be in a folder called "Output".')


if __name__ == "__main__":
    main()
