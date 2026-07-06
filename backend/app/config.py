"""应用配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    DEEPSEEK_MAX_TOKENS: int = 4096
    DEEPSEEK_TEMPERATURE: float = 0.1

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
    DATA_DIR: str = os.getenv("DATA_DIR", str(BASE_DIR / "data" / "storage"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ANALYSIS_SAMPLE_SIZE: int = 10

    # PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATA_ENCRYPTION_KEY: str = os.getenv("DATA_ENCRYPTION_KEY", "")
    AUTH_SECRET: str = os.getenv("AUTH_SECRET", DATA_ENCRYPTION_KEY)
    AUTH_TOKEN_HOURS: int = int(os.getenv("AUTH_TOKEN_HOURS", "12"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"


settings = Settings()
