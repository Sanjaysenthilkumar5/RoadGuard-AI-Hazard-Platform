import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_ASSETS_DIR = BASE_DIR / "app" / "static" / "assets"
SAMPLE_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "RoadGuard AI"
    VERSION: str = "2.4.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "roadguard-secret-key-prod-super-secure-jwt-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/roadguard.db")
    
    # Computer Vision Settings
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.50
    DUPLICATE_DISTANCE_METERS: float = 18.0  # Proximity threshold for duplicate hazards
    VIDEO_FPS_SAMPLE_RATE: int = 5          # Frame sampling rate for video analysis
    
    # Active AI Model Version
    ACTIVE_MODEL_VERSION: str = "RoadGuard-YOLO-v2.4"
    MODEL_VERSIONS: list[str] = [
        "RoadGuard-YOLO-v1.0-MobileNet",
        "RoadGuard-YOLO-v2.0-Standard",
        "RoadGuard-YOLO-v2.4-Transformer"
    ]

settings = Settings()
