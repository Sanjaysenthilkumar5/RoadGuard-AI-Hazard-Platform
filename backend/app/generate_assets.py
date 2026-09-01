import os
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "static" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def generate_sample_assets():
    w, h = 640, 400

    # 1. Sample Pothole Road
    img1 = Image.new("RGB", (w, h), "#0f172a")
    draw1 = ImageDraw.Draw(img1)
    # Perspective asphalt
    draw1.polygon([(0, h), (w, h), (int(w * 0.7), int(h * 0.4)), (int(w * 0.3), int(h * 0.4))], fill="#1e293b")
    draw1.rectangle([(0, 0), (w, int(h * 0.4))], fill="#090d16")
    # Lane stripes
    draw1.line([(int(w * 0.5), int(h * 0.4)), (int(w * 0.5), h)], fill="#e2e8f0", width=4)
    draw1.line([(int(w * 0.35), int(h * 0.4)), (int(w * 0.05), h)], fill="#fbbf24", width=3)
    draw1.line([(int(w * 0.65), int(h * 0.4)), (int(w * 0.95), h)], fill="#fbbf24", width=3)
    # Pothole cavity
    draw1.ellipse([(int(w * 0.38), int(h * 0.62)), (int(w * 0.62), int(h * 0.82))], fill="#020617", outline="#475569", width=3)
    img1.save(ASSETS_DIR / "sample_pothole.jpg", format="JPEG", quality=90)

    # 2. Sample Repaired Road
    img2 = Image.new("RGB", (w, h), "#0f172a")
    draw2 = ImageDraw.Draw(img2)
    draw2.polygon([(0, h), (w, h), (int(w * 0.7), int(h * 0.4)), (int(w * 0.3), int(h * 0.4))], fill="#1e293b")
    draw2.rectangle([(0, 0), (w, int(h * 0.4))], fill="#090d16")
    # Fresh smooth patch
    draw2.ellipse([(int(w * 0.35), int(h * 0.60)), (int(w * 0.65), int(h * 0.84))], fill="#090d16", outline="#334155", width=2)
    # Bright new stripes
    draw2.line([(int(w * 0.5), int(h * 0.4)), (int(w * 0.5), h)], fill="#38bdf8", width=4)
    draw2.line([(int(w * 0.35), int(h * 0.4)), (int(w * 0.05), h)], fill="#fbbf24", width=3)
    draw2.line([(int(w * 0.65), int(h * 0.4)), (int(w * 0.95), h)], fill="#fbbf24", width=3)
    img2.save(ASSETS_DIR / "sample_repaired_road.jpg", format="JPEG", quality=90)

    print(f"Generated sample assets in: {ASSETS_DIR}")

if __name__ == "__main__":
    generate_sample_assets()
