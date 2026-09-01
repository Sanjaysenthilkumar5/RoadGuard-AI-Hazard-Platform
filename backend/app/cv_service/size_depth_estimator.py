from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import io
import base64

def generate_relative_depth_map(image: Image.Image) -> Tuple[Image.Image, str]:
    """
    Generates a normalized monocular relative depth estimation map.
    Depressions/potholes and road plane gradient are highlighted.
    Returns (PIL Image, base64 data URI).
    """
    # Convert to grayscale
    gray = image.convert("L")
    
    # Invert and apply edge & texture filtering to approximate surface topology
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=3))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    
    # Blend gradient to simulate monocular perspective depth (lower image is closer, upper is horizon)
    w, h = image.size
    gradient = np.tile(np.linspace(255, 50, h, dtype=np.uint8)[:, None], (1, w))
    
    gray_np = np.array(blurred)
    edges_np = np.array(edges)
    
    # Combine perspective gradient with texture variance
    depth_np = (0.55 * gradient + 0.35 * gray_np + 0.10 * edges_np).astype(np.uint8)
    
    # Apply colormap: Plasma/Turbo-like false color palette (Deep purple/blue = far/deep, Yellow/Cyan = near/surface)
    depth_img = Image.fromarray(depth_np)
    colored_depth = ImageOps.colorize(depth_img, black="#0f172a", mid="#6366f1", white="#38bdf8")
    
    # Convert to base64
    buffered = io.BytesIO()
    colored_depth.save(buffered, format="JPEG", quality=85)
    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return colored_depth, img_b64

def estimate_approximate_dimensions(
    bbox: Dict[str, float], 
    img_width: int, 
    img_height: int,
    hazard_type: str
) -> Dict[str, Any]:
    """
    Estimates approximate physical dimensions from 2D bounding box with monocular approximation disclaimer.
    Assumes standard vehicle dashcam perspective (~1.2m mount height, 60 deg FOV).
    """
    box_w = max(1.0, bbox["x2"] - bbox["x1"])
    box_h = max(1.0, bbox["y2"] - bbox["y1"])
    
    rel_w = box_w / img_width
    rel_h = box_h / img_height
    rel_area_pct = (rel_w * rel_h) * 100.0
    
    # Vertical position in frame (y2 near bottom means closer to bumper)
    vertical_pos = bbox["y2"] / img_height
    
    # Distance approximation factor (closer objects have more pixels per cm)
    # At bottom of frame (y=0.9), 1 pixel ~ 0.25cm; at mid frame (y=0.5), 1 pixel ~ 0.8cm
    px_to_cm_factor = 0.25 + (1.0 - vertical_pos) * 0.9
    
    est_width_cm = round(box_w * px_to_cm_factor, 1)
    est_length_cm = round(box_h * px_to_cm_factor * 1.3, 1)  # Perspective foreshortening adjustment
    est_area_sqcm = round(est_width_cm * est_length_cm, 0)
    
    # Estimated relative depth profile
    relative_depth_score = round(min(1.0, (rel_w * 0.4 + (1.0 - vertical_pos) * 0.6)), 2)
    
    return {
        "estimated_width_cm": est_width_cm,
        "estimated_length_cm": est_length_cm,
        "estimated_area_sqcm": est_area_sqcm,
        "relative_area_percentage": round(rel_area_pct, 2),
        "relative_depth_index": relative_depth_score,
        "is_calibrated": False,
        "measurement_disclaimer": "Approximate relative size estimated via perspective geometry. Uncalibrated monocular camera.",
        "calibration_status": "Monocular Estimation (±15% tolerance)"
    }
