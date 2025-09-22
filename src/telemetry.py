"""OpenTelemetry configuration for SAVT application."""

import os
import sys

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from .logging_config import get_logger

logger = get_logger(__name__)


def setup_telemetry(app):
    """Configure OpenTelemetry tracing for the FastAPI application."""
    try:
        # Skip telemetry setup during tests to avoid I/O issues
        if "pytest" in sys.modules or os.getenv("TESTING"):
            logger.info("Skipping OpenTelemetry setup during tests")
            return

        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # Use console exporter for development (Phase 1)
        # In production, this would be replaced with OTLP exporter
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Instrument FastAPI automatically
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")

        # Instrument SQLAlchemy automatically
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation enabled")

        logger.info("OpenTelemetry tracing setup completed")

    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
        # Don't fail the application if telemetry setup fails
