"""
OpenTelemetry tracing setup.
"""
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Resource attributes
resource = Resource.create({
    "service.name": "rag-application",
    "service.version": "1.0.0",
})

# Setup tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))

# OTLP exporter (can be configured via environment variables)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

# Add span processor
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)


def setup_tracing():
    """Initialize tracing configuration."""
    # Tracing is already set up via module-level code
    pass


def get_tracer(name: str):
    """Get a tracer instance."""
    return trace.get_tracer(name)
