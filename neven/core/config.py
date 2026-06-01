"""
NEVEN Configuration Management
Handles environment variables, config files, and runtime settings.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class NevenConfig:
    """Central configuration for the NEVEN platform."""

    # API Configuration
    api_key: str = ""
    agent_private_key: str = ""
    base_url: str = "http://localhost:8420"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8420
    workers: int = 4
    debug: bool = False

    # Perception Configuration
    detection_confidence: float = 0.35
    tracking_max_age: int = 30
    frame_rate: int = 15
    detection_model: str = "yolov8n"

    # Safety Engine Configuration
    safety_enabled: bool = True
    max_actuation_frequency_seconds: float = 10.0
    fail_safe_default: str = "locked"

    # Storage Configuration
    redis_url: str = "redis://localhost:6379"
    database_url: str = "sqlite:///neven.db"

    # Analytics Configuration
    analytics_enabled: bool = True
    heatmap_resolution: int = 50
    dwell_time_threshold_seconds: float = 5.0

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "NevenConfig":
        """Load configuration from environment variables."""
        return cls(
            api_key=os.getenv("NEVEN_API_KEY", ""),
            agent_private_key=os.getenv("NEVEN_AGENT_PRIVATE_KEY", ""),
            base_url=os.getenv("NEVEN_BASE_URL", "http://localhost:8420"),
            host=os.getenv("NEVEN_HOST", "0.0.0.0"),
            port=int(os.getenv("NEVEN_PORT", "8420")),
            workers=int(os.getenv("NEVEN_WORKERS", "4")),
            debug=os.getenv("NEVEN_DEBUG", "false").lower() == "true",
            detection_confidence=float(os.getenv("NEVEN_DETECTION_CONFIDENCE", "0.35")),
            tracking_max_age=int(os.getenv("NEVEN_TRACKING_MAX_AGE", "30")),
            frame_rate=int(os.getenv("NEVEN_FRAME_RATE", "15")),
            detection_model=os.getenv("NEVEN_DETECTION_MODEL", "yolov8n"),
            safety_enabled=os.getenv("NEVEN_SAFETY_ENABLED", "true").lower() == "true",
            max_actuation_frequency_seconds=float(
                os.getenv("NEVEN_MAX_ACTUATION_FREQ", "10.0")
            ),
            redis_url=os.getenv("NEVEN_REDIS_URL", "redis://localhost:6379"),
            database_url=os.getenv(
                "NEVEN_DATABASE_URL", "sqlite:///neven.db"
            ),
            analytics_enabled=os.getenv("NEVEN_ANALYTICS_ENABLED", "true").lower()
            == "true",
            heatmap_resolution=int(os.getenv("NEVEN_HEATMAP_RESOLUTION", "50")),
            dwell_time_threshold_seconds=float(
                os.getenv("NEVEN_DWELL_THRESHOLD", "5.0")
            ),
            log_level=os.getenv("NEVEN_LOG_LEVEL", "INFO"),
            log_file=os.getenv("NEVEN_LOG_FILE"),
        )

    @classmethod
    def from_file(cls, path: str) -> "NevenConfig":
        """Load configuration from a JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(config_path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        from dataclasses import asdict
        return asdict(self)

    def save(self, path: str) -> None:
        """Save configuration to a JSON file."""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
