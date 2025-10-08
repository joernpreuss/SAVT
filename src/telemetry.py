"""OpenTelemetry configuration for SAVT application."""

import os
import sys

from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import start_http_server

from .logging_config import get_logger

logger = get_logger(__name__)


def setup_telemetry(app):
    """Configure OpenTelemetry tracing and metrics for the FastAPI application."""
    try:
        # Skip telemetry setup by default (enable with ENABLE_TELEMETRY=1)
        if not os.getenv("ENABLE_TELEMETRY"):
            return

        # Skip telemetry setup during tests to avoid I/O issues
        if "pytest" in sys.modules or os.getenv("TESTING"):
            logger.info("Skipping OpenTelemetry setup during tests")
            return

        # Set up metrics provider with Prometheus exporter
        prometheus_reader = PrometheusMetricReader()
        metrics.set_meter_provider(MeterProvider(metric_readers=[prometheus_reader]))

        # Start Prometheus metrics server on port 8080 (or next available port)
        metrics_port = 8080
        try:
            start_http_server(metrics_port)
            logger.info(f"Prometheus metrics server started on port {metrics_port}")
        except OSError:
            # Try next port if 8080 is busy
            metrics_port = 8081
            start_http_server(metrics_port)
            logger.info(f"Prometheus metrics server started on port {metrics_port}")

        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # Use console exporter for development (Phase 1)
        # In production, this would be replaced with OTLP exporter
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)  # type: ignore[attr-defined]

        # Instrument FastAPI automatically
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")

        # Instrument SQLAlchemy automatically
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation enabled")

        logger.info("OpenTelemetry tracing and metrics setup completed")

    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
        # Don't fail the application if telemetry setup fails
