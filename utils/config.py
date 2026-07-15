"""
Configuration management for Niklaus plagiarism detector.
"""

from dataclasses import dataclass
from typing import Tuple
import os


@dataclass
class Config:
    """Application configuration."""
    
    # API Settings
    MARITACA_API_URL: str = "https://chat.maritaca.ai/api"
    MARITACA_MODEL: str = "sabiazinho-4"
    MARITACA_TIMEOUT: int = 30
    MARITACA_MAX_RETRIES: int = 3
    MARITACA_RATE_LIMIT: int = 30  # calls per minute
    
    # File Settings
    MAX_ZIP_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: Tuple[str, ...] = ('.py', '.c', '.cpp', '.java', '.js', 
                                             '.ts', '.go', '.rs', '.kt')
    
    # Processing Settings
    PARALLEL_WORKERS: int = 4
    BATCH_SIZE: int = 10
    
    # Cache Settings
    CACHE_DIR: str = ".niklaus_cache"
    CACHE_EXPIRY_HOURS: int = 24
    
    # UI Settings
    DEFAULT_THRESHOLD: float = 0.7
    
    # Language Extensions Mapping
    LANGUAGE_EXTENSIONS: dict = None
    
    def __post_init__(self):
        """Initialize language extensions mapping."""
        if self.LANGUAGE_EXTENSIONS is None:
            self.LANGUAGE_EXTENSIONS = {
                "Python": "py",
                "C": "c",
                "C++": "cpp",
                "Java": "java",
                "JavaScript": "js",
                "Go": "go",
                "Rust": "rs",
                "TypeScript": "ts",
                "Kotlin": "kt",
            }
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        return cls(
            MARITACA_MODEL=os.getenv('MARITACA_MODEL', cls.MARITACA_MODEL),
            MARITACA_TIMEOUT=int(os.getenv('MARITACA_TIMEOUT', str(cls.MARITACA_TIMEOUT))),
            MARITACA_RATE_LIMIT=int(os.getenv('MARITACA_RATE_LIMIT', str(cls.MARITACA_RATE_LIMIT))),
            PARALLEL_WORKERS=int(os.getenv('PARALLEL_WORKERS', str(cls.PARALLEL_WORKERS))),
            MAX_ZIP_SIZE_MB=int(os.getenv('MAX_ZIP_SIZE_MB', str(cls.MAX_ZIP_SIZE_MB))),
            CACHE_EXPIRY_HOURS=int(os.getenv('CACHE_EXPIRY_HOURS', str(cls.CACHE_EXPIRY_HOURS))),
            DEFAULT_THRESHOLD=float(os.getenv('DEFAULT_THRESHOLD', str(cls.DEFAULT_THRESHOLD))),
        )


config = Config.from_env()