# ce_logger.py
import logging
from logging.handlers import RotatingFileHandler
from capital_group.configs import config
import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

def get_logger(name: str = __name__) -> logging.Logger:
    """
    Returns a configured logger with both console and file handlers.
    RotatingFileHandler avoids unlimited log file growth.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler with rotation (max 5MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(
            filename='capital_group.log',
            maxBytes=5*1024*1024,
            backupCount=5
        )
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# --- DATABASE SETUP (New) ---
# This creates a file named 'scraped_data.db' in your root folder
import os

# DB_PATH = "sqlite:///./scraped_data.db"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = f"sqlite:///{os.path.join(BASE_DIR, '../../scraped_data.db')}"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScrapedResult(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create the table immediately
Base.metadata.create_all(bind=engine)