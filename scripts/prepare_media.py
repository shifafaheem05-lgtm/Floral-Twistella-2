#!/usr/bin/env python3
"""
prepare_media.py
================
Turns the raw files in  originals/  into ready-to-post, logo-branded files in  media/ :

  originals/day_07.jpeg  ->  media/day_07.jpg   (cropped to Instagram-safe ratio + logo)
  originals/day_03.mp4   ->  media/day_03.mp4   (1080x1920 Reel, 30 fps, H.264 + logo)

Run it whenever you replace assets/logo.png or add/replace an original:

    python scripts/prepare_media.py                 # everything
    python scripts/prepare_media.py --days 3 7 12   # only some days
    python scripts/prepare_media.py --logo my_logo.png

Requirements: Pillow, and ffmpeg/ffprobe on PATH (for videos).
Settings (logo size/position, manual crops) live in media_config.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
ORIGINALS = ROOT / "originals"
MEDIA = ROOT / "media"
CONFIG_FILE = ROOT / "media_config.json"
DEFAULT_LOGO = ROOT / "assets" / "logo.png"

VIDEO_EXT = {".mp4", ".mov", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MIN_RATIO, MAX_RATIO = 0.8, 1.91  # Instagram feed limits (4:5 to 1.91:1)


def load_config() -> dict:
    with CONFIG_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Logo
# --------------------------------------------------------------------------- #
def load_logo(path: Path) -> Image.Image:
    if not path.exists():
        sys.exit(f"Logo not found: {path}\nCreate a placeholder with: python scripts/make_placeholder_logo.py")
    return Image.open(path).convert("RGBA")


def scaled_logo(logo: Image.Image, target_width: int, opacity: float) -> Image.Image:
    height = round(logo.height * target_width / logo.width)
    out = logo.resize((target_width, height), Image.LANCZOS)
    if opacity < 1:
        alpha = out.getchannel("A").point(lambda a: int(a * opacity))
        out.putalpha(alpha)
    return out


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #
def process_image(src: Path, dst: Path, day: int, cfg: dict, logo: Image.Image) -> None:
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")

    box = cfg.get("crops", {}).get(f"day_{day:02d}")
    if box:  # manual crop (e.g. remove screenshot bars)
        img = img.crop(tuple(box))

    w, h = img.size
    if w / h < MIN_RATIO:  # too tall for an Instagram feed post -> trim top/bottom evenly
        new_h = int(w / MIN_RATIO)  # floor so the ratio never dips below 4:5
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    elif w / h > MAX_RATIO:  # too wide -> trim left/right evenly
        new_w = int(h * MAX_RATIO)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))

    if img.width > cfg["image"]["max_width"]:
        scale = cfg["image"]["max_width"] / img.width
        img = img.resize((cfg["image"]["max_width"], round(img.height * scale)), Image.LANCZOS)

    lg = scaled_logo(logo, round(img.width * cfg["logo"]["image_width_pct"]), cfg["logo"]["opacity"])
    margin = round(img.width * cfg["logo"]["margin_pct"])
    pos = cfg["logo"]["image_position"]
    x = margin if "left" in pos else img.width - lg.width - margin
    y = margin if "top" in pos else img.height - lg.height - margin
    img = img.convert("RGBA")
    img.alpha_composite(lg, (x, y))
    img.convert("RGB").save(dst, "JPEG", quality=cfg["image"]["quality"], optimize=True)


# --------------------------------------------------------------------------- #
# Videos
# --------------------------------------------------------------------------- #
def probe(src: Path) -> tuple[int, int, bool]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip()
    w, h = (int(v) for v in out.split(",")[:2])
    audio = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip()
    return w, h, bool(audio)


def process_video(src: Path, dst: Path, cfg: dict, logo_path: Path, logo: Image.Image) -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found - install it to process videos.")
    vc = cfg["video"]
    W, H = vc["width"], vc["height"]
    w, h, has_audio = probe(src)

    logo_w = round(W * cfg["logo"]["video_width_pct"])
    logo_h = round(logo.height * logo_w / logo.width)
    margin = round(W * cfg["logo"]["margin_pct"])
    pos = cfg["logo"]["video_position"]

    if w / h > 0.7:
        # Square / landscape clip -> centre it on a blurred 9:16 canvas (proper Reel format)
        fg_h = round(W * h / w / 2) * 2
        top = (H - fg_h) // 2
        bottom = top + fg_h
        base = (
            "[0:v]fps={fps},split=2[a][b];"
            "[a]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},gblur=sigma=10,"
            "scale={W}:{H},eq=brightness=-0.06[bg];"
            "[b]scale={W}:{fg_h}:flags=lanczos[fg];"
            "[bg][fg]overlay=0:{top}[base];"
        ).format(fps=vc["fps"], bw=W // 4, bh=H // 4, W=W, H=H, fg_h=fg_h, top=top)
        area_top, area_bottom = top, bottom
    else:
        # Already vertical -> fill 9:16
        base = (
            "[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}[base];"
        ).format(fps=vc["fps"], W=W, H=H)
        # keep clear of Instagram's top/bottom UI zones
        area_top, area_bottom = round(H * 0.14), round(H * 0.65)

    x = margin if "left" in pos else W - logo_w - margin
    y = area_top + margin if "top" in pos else area_bottom - logo_h - margin

    graph = (
        base
        + "[1:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={op}[lg];"
          "[base][lg]overlay={x}:{y}:format=auto,format=yuv420p[out]"
    ).format(lw=logo_w, op=cfg["logo"]["opacity"], x=x, y=y)

    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-i", str(logo_path),
           "-filter_complex", graph, "-map", "[out]"]
    if has_audio:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ar", "44100"]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", str(vc["crf"]),
            "-r", str(vc["fps"]), "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Crop, brand and format media for posting")
    ap.add_argument("--days", type=int, nargs="*", help="Only these day numbers")
    ap.add_argument("--logo", type=Path, default=DEFAULT_LOGO, help="Logo PNG (transparent background)")
    args = ap.parse_args()

    cfg = load_config()
    logo = load_logo(args.logo)
    MEDIA.mkdir(exist_ok=True)

    files = sorted(p for p in ORIGINALS.iterdir() if p.stem.startswith("day_"))
    done = 0
    for src in files:
        day = int(src.stem.split("_")[1])
        if args.days and day not in args.days:
            continue
        ext = src.suffix.lower()
        if ext in VIDEO_EXT:
            dst = MEDIA / f"day_{day:02d}.mp4"
            process_video(src, dst, cfg, args.logo, logo)
        elif ext in IMAGE_EXT:
            dst = MEDIA / f"day_{day:02d}.jpg"
            process_image(src, dst, day, cfg, logo)
        else:
            print(f"skip {src.name}")
            continue
        print(f"day {day:>2}: {src.name} -> media/{dst.name}")
        done += 1
    print(f"Done - {done} file(s) written to media/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
