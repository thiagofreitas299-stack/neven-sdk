"""
NEVEN Logging Configuration
"""

import logging
import sys
from typing import Optional


NEVEN_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ██╗███████╗██╗   ██╗███████╗███╗   ██╗            ║
║   ████╗  ██║██╔════╝██║   ██║██╔════╝████╗  ██║            ║
║   ██╔██╗ ██║█████╗  ██║   ██║█████╗  ██╔██╗ ██║            ║
║   ██║╚██╗██║██╔══╝  ╚██╗ ██╔╝██╔══╝  ██║╚██╗██║            ║
║   ██║ ╚████║███████╗ ╚████╔╝ ███████╗██║ ╚████║            ║
║   ╚═╝  ╚═══╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝            ║
║                                                              ║
║   AI · SMART CITY SOLUTIONS                                  ║
║   The Physical World Runtime — v1.0.0                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


class NevenFormatter(logging.Formatter):
    """Custom formatter with NEVEN branding colors."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[34m",      # Blue
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.name = f"{self.BOLD}{record.name}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    show_banner: bool = True,
) -> None:
    """
    Configure NEVEN logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
        show_banner: Whether to print the NEVEN banner
    """
    if show_banner:
        print(NEVEN_BANNER)

    # Configure root logger
    root_logger = logging.getLogger("neven")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        NevenFormatter("%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s")
    )
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
