import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "eye-login-api")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "models/best.pt")
    CUDA_DEVICE: str | int = os.getenv("CUDA_DEVICE", "0")
    CONF_THRESHOLD: float = float(os.getenv("CONF_THRESHOLD", "0.85"))

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_me")
    JWT_EXPIRE_MIN: int = int(os.getenv("JWT_EXPIRE_MIN", "60"))

settings = Settings()