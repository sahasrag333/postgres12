import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """
    Central Configuration class. 
    Maintains a single source of truth for Flask, Celery, and AWS settings.
    """
    
    # General Project Settings
    PROJECT_NAME = "capital_group"
    BASE_DIR = Path(__file__).resolve().parent.parent
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Flask Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "highly-secret-fallback-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # Redis / Celery Settings
    # Defaulting to localhost for local dev; overrides via ENV for Docker/K8s
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    
    CELERY_BROKER_URL = os.getenv(
        "CELERY_BROKER_URL", 
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    )
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", 
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    )

    # Database Settings
    DB_USER = os.getenv("DB_USER", "postgres_sah")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres_sah")
    DB_HOST = os.getenv("DB_HOST", "my-postgres-db-sah.cfwa4gyoiqvq.ap-south-2.rds.amazonaws.com")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AWS / S3 Settings
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")

    # Selenium / Scraping Settings
    SELENIUM_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444/wd/hub")
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    @staticmethod
    def validate_config():
        """
        Check for critical missing variables before the app starts.
        """
        critical_vars = [os.getenv("SECRET_KEY")]
        if not all(critical_vars) and not Config.DEBUG:
            raise ValueError("Missing critical Environment Variables for Production!")

# Create a config instance to be imported elsewhere
config = Config()