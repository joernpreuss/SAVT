import logging
import sys
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler

from .config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure logging for the application.

    Args:
        log_level: Override the log level from settings
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if settings.debug else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Console handler with Rich for better formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_path=settings.debug,
        show_time=False,  # We handle time in formatter
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler for production or when explicitly requested
    if not settings.debug or settings.log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "savt.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set root logger level
    root_logger.setLevel(level)

    # Configure third-party loggers
    _configure_third_party_loggers()

    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {logging.getLevelName(level)}")


def _configure_third_party_loggers() -> None:
    """Configure logging levels for third-party libraries."""
    # SQLAlchemy can be very verbose
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Uvicorn access logs (let FastAPI handle request logging)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Keep uvicorn server logs at INFO
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
