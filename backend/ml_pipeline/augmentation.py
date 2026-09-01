"""
RoadGuard AI - Adverse Weather & Pavement Augmentation Pipeline
Simulates realistic driving conditions: Day, Night, Rain streaks, Fog, Motion Blur, Shadows, and Perspective Warping.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import random

def simulate_rain_streaks(image: Image.Image, streak_density: int = 150) -> Image.Image:
    """Injects motion-blurred translucent rain streaks simulating dashboard camera in wet weather."""
    img = image.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    
    for _ in range(streak_density):
        x1 = random.randint(0, w)
        y1 = random.randint(0, h)
        length = random.randint(15, 35)
        angle = 75  # ~75 degree rain slant
        x2 = int(x1 + length * np.cos(np.radians(angle)))
        y2 = int(y1 + length * np.sin(np.radians(angle)))
        opacity = random.randint(100, 180)
        draw.line([(x1, y1), (x2, y2)], fill=(220, 230, 245, opacity), width=1)
        
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.5))
    img.paste(overlay, (0, 0), overlay)
    return img

def simulate_low_light_night(image: Image.Image, brightness_factor: float = 0.35) -> Image.Image:
    """Simulates night driving headlights illumination."""
    enhancer = ImageEnhance.Brightness(image)
    darkened = enhancer.enhance(brightness_factor)
    
    # Add headlight beam mask
    w, h = image.size
    beam_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(beam_mask)
    draw.polygon([(int(w*0.2), h), (int(w*0.8), h), (int(w*0.55), int(h*0.4)), (int(w*0.45), int(h*0.4))], fill=180)
    beam_mask = beam_mask.filter(ImageFilter.GaussianBlur(radius=25))
    
    bright_center = ImageEnhance.Brightness(image).enhance(0.9)
    darkened.paste(bright_center, (0, 0), beam_mask)
    return darkened

def apply_motion_blur(image: Image.Image, radius: int = 2) -> Image.Image:
    """Simulates high-speed camera vehicle vibration/blur."""
    return image.filter(ImageFilter.GaussianBlur(radius=radius))
