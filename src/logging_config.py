import logging
from pathlib import Path

import structlog
from opentelemetry import trace
from rich.logging import RichHandler

from .config import settings


def setup_logging(log_level: str | None = None) -> None:
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

    # Configure structlog
    _configure_structlog()

    # Log configuration
    logger = get_logger(__name__)
    logger.info("Logging configured", level=logging.getLevelName(level))


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


def _add_trace_context(logger, method_name, event_dict):
    """Add OpenTelemetry trace context to log entries."""
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            event_dict["trace_id"] = f"0x{format(span_context.trace_id, '032x')}"
            event_dict["span_id"] = f"0x{format(span_context.span_id, '016x')}"
    return event_dict


def _configure_structlog() -> None:
    """Configure structlog for enhanced structured logging."""
    # Configure structlog to output directly (not through stdlib logging)
    # This avoids conflicts with existing Rich logging setup
    if settings.debug:
        # Development: Pretty console output with trace context
        processors = [
            _add_trace_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=False),
        ]
        logger_factory = structlog.WriteLoggerFactory()
        wrapper_class = structlog.make_filtering_bound_logger(logging.INFO)
    else:
        # Production: JSON to stdout with trace context
        processors = [
            _add_trace_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
        logger_factory = structlog.WriteLoggerFactory()
        wrapper_class = structlog.make_filtering_bound_logger(logging.INFO)

    structlog.configure(
        processors=processors,
        logger_factory=logger_factory,
        wrapper_class=wrapper_class,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)
