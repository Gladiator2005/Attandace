from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API
    app_name: str = "Face Recognition Attendance"
    api_version: str = "1.0.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./attendance.db"
    database_echo: bool = False

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 3

    # Face Recognition
    face_confidence_threshold: float = 60.0
    knn_k: int = 5

    # File Upload
    max_upload_size: int = 10 * 1024 * 1024
    upload_dir: str = "./uploads"

    # Email (optional for dev)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@attendance.local"

    # Attendance locking
    attendance_lock_days: int = 3  # records lock after this many days

    # Campus location (set to 0.0 to disable GPS check)
    campus_lat: float = 0.0
    campus_lng: float = 0.0
    campus_radius_km: float = 0.5

    # Redis (optional)
    redis_url: str = ""

    # Celery (optional)
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # CORS
    cors_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
