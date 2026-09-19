#!/usr/bin/env python3
"""
Creates assets/logo.png - a PLACEHOLDER "Floral Twistella" wordmark (transparent PNG).

Replace assets/logo.png with your real logo (PNG with transparent background, roughly
1200 px wide) and run:  python scripts/prepare_media.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, size)
            try:
                font.set_variation_by_axes([700])  # bold weight on variable fonts
            except Exception:
                pass
            return font
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    scale = 3  # draw large, then downsample for smooth edges
    W, H = 1200 * scale, 300 * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # soft pill background so the logo reads on light AND dark photos
    d.rounded_rectangle((6 * scale, 6 * scale, W - 6 * scale, H - 6 * scale), radius=H // 2,
                        fill=(255, 255, 255, 228), outline=(226, 130, 160, 255), width=5 * scale)

    # simple six-petal flower mark
    cx, cy, r = 165 * scale, H // 2, 70 * scale
    import math
    for k in range(6):
        ang = math.radians(k * 60)
        px, py = cx + math.cos(ang) * r * 0.62, cy + math.sin(ang) * r * 0.62
        d.ellipse((px - r * 0.42, py - r * 0.42, px + r * 0.42, py + r * 0.42), fill=(232, 116, 150, 255))
    d.ellipse((cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3), fill=(255, 208, 110, 255))

    font = load_font(118 * scale)
    text = "Floral Twistella"
    bbox = d.textbbox((0, 0), text, font=font)
    tx = 290 * scale
    ty = (H - (bbox[3] - bbox[1])) // 2 - bbox[1]
    d.text((tx, ty), text, font=font, fill=(133, 38, 76, 255))

    img = img.resize((W // scale, H // scale), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"Placeholder logo written to {OUT}")


if __name__ == "__main__":
    main()
