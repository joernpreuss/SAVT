"""Business metrics for SAVT application."""

from opentelemetry import metrics

from .logging_config import get_logger

logger = get_logger(__name__)

# Get meter for creating instruments
meter = metrics.get_meter(__name__)

# HTTP Request Metrics
http_request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="Duration of HTTP requests in seconds",
    unit="s",
)

http_requests_total = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
)

http_request_errors = meter.create_counter(
    name="http_request_errors_total",
    description="Total number of HTTP request errors",
)

# Database Metrics
db_query_duration = meter.create_histogram(
    name="db_query_duration_seconds",
    description="Duration of database queries in seconds",
    unit="s",
)

db_connections_active = meter.create_up_down_counter(
    name="db_connections_active",
    description="Number of active database connections",
)

# Business Metrics
features_created_total = meter.create_counter(
    name="features_created_total",
    description="Total number of features created",
)

features_vetoed_total = meter.create_counter(
    name="features_vetoed_total",
    description="Total number of features vetoed",
)

items_created_total = meter.create_counter(
    name="items_created_total",
    description="Total number of items created",
)

veto_operations_total = meter.create_counter(
    name="veto_operations_total",
    description="Total number of veto/unveto operations",
)

# Current state metrics
features_active = meter.create_up_down_counter(
    name="features_active",
    description="Number of currently active features",
)

items_active = meter.create_up_down_counter(
    name="items_active",
    description="Number of currently active items",
)


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    labels = {"method": method, "endpoint": endpoint, "status_code": str(status_code)}

    http_request_duration.record(duration, labels)
    http_requests_total.add(1, labels)

    if status_code >= 400:
        http_request_errors.add(1, labels)


def record_feature_created(feature_type: str = "unknown"):
    """Record when a feature is created."""
    features_created_total.add(1, {"type": feature_type})
    features_active.add(1)


def record_feature_vetoed(veto_action: str):
    """Record when a feature is vetoed or unvetoed."""
    features_vetoed_total.add(1, {"action": veto_action})
    veto_operations_total.add(1, {"action": veto_action})


def record_item_created(item_type: str = "unknown"):
    """Record when an item is created."""
    items_created_total.add(1, {"type": item_type})
    items_active.add(1)


def record_db_query(operation: str, duration: float):
    """Record database query metrics."""
    db_query_duration.record(duration, {"operation": operation})


logger.info("Business metrics instruments created")
