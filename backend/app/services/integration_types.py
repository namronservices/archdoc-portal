"""Integration type taxonomy.

Single source of truth for the supported integration types: their templates,
contract conventions, and type-aware metadata field schemas. Drives the
metadata form, ``metadata.yaml`` serialization, and validation.
"""
from __future__ import annotations


def _f(key: str, label: str, kind: str = "text", options: list[str] | None = None) -> dict:
    """Build one metadata field spec."""
    spec: dict = {"key": key, "label": label, "kind": kind}
    if options:
        spec["options"] = options
    return spec


STREAMING_MODES = [
    "unary",
    "server_streaming",
    "client_streaming",
    "bidirectional_streaming",
]


# type -> definition. ``metadata_fields`` drives the type-aware form + yaml.
INTEGRATION_TYPE_DEFS: dict[str, dict] = {
    "GRPC": {
        "label": "gRPC",
        "priority": "highest",
        "contract_format": "PROTOBUF",
        "contract_extension": ".proto",
        "template": "grpc",
        "metadata_fields": [
            _f("protocol", "Protocol", "select", ["HTTP_2"]),
            _f("proto_package", "Proto package"),
            _f("grpc_service", "gRPC service name"),
            _f("methods", "RPC methods", "list"),
            _f("communication_pattern", "Communication pattern", "select",
               ["synchronous", "asynchronous"]),
            _f("streaming_type", "Streaming type", "select", STREAMING_MODES),
            _f("authentication", "Authentication", "select",
               ["mTLS", "token", "none"]),
            _f("authorization", "Authorization"),
            _f("deadline_ms", "Deadline / timeout (ms)"),
            _f("retry_policy", "Retry policy", "select",
               ["no_retry", "bounded_retry", "unbounded_retry"]),
            _f("idempotency_required", "Idempotency required", "bool"),
            _f("data_classification", "Data classification", "select",
               ["public", "internal", "confidential", "restricted"]),
        ],
    },
    "KAFKA": {
        "label": "Kafka",
        "priority": "highest",
        "contract_format": "ASYNCAPI",
        "contract_extension": ".yaml",
        "template": "kafka",
        "metadata_fields": [
            _f("producer", "Producer"),
            _f("consumer", "Consumer"),
            _f("topic", "Topic"),
            _f("schema_format", "Schema format", "select",
               ["AVRO", "JSON_SCHEMA", "PROTOBUF"]),
            _f("ordering_key", "Ordering key"),
            _f("retention", "Retention"),
            _f("replay_supported", "Replay supported", "bool"),
            _f("dlq_behavior", "DLQ behavior"),
            _f("consumer_group", "Consumer group"),
            _f("idempotent_processing", "Idempotent processing", "bool"),
        ],
    },
    "MQ": {
        "label": "MQ",
        "priority": "high",
        "contract_format": "MESSAGE_SCHEMA",
        "contract_extension": ".xsd",
        "template": "mq",
        "metadata_fields": [
            _f("queue_name", "Queue name"),
            _f("delivery_guarantee", "Delivery guarantee", "select",
               ["at_most_once", "at_least_once", "exactly_once"]),
            _f("retry_behavior", "Retry behavior"),
            _f("dead_letter_queue", "Dead-letter queue"),
            _f("correlation_id", "Correlation ID"),
            _f("transactional", "Transactional", "bool"),
            _f("ordering_required", "Ordering required", "bool"),
        ],
    },
    "SOAP": {
        "label": "Legacy SOAP",
        "priority": "high",
        "contract_format": "WSDL",
        "contract_extension": ".wsdl",
        "template": "soap",
        "metadata_fields": [
            _f("soap_action", "SOAP action"),
            _f("endpoint", "Endpoint URL"),
            _f("authentication", "Authentication"),
            _f("timeout_ms", "Timeout (ms)"),
            _f("retry_policy", "Retry policy"),
            _f("fault_handling", "SOAP fault handling"),
            _f("legacy_constraints", "Legacy constraints"),
        ],
    },
    "REST": {
        "label": "REST",
        "priority": "medium",
        "contract_format": "OPENAPI",
        "contract_extension": ".yaml",
        "template": "rest",
        "metadata_fields": [
            _f("base_path", "Base path"),
            _f("methods", "HTTP methods", "list"),
            _f("authentication", "Authentication"),
            _f("versioning", "Versioning strategy"),
        ],
    },
    "FILE": {
        "label": "File transfer",
        "priority": "medium",
        "contract_format": "FILE_LAYOUT",
        "contract_extension": ".txt",
        "template": "file-transfer",
        "metadata_fields": [
            _f("file_format", "File format"),
            _f("transfer_protocol", "Transfer protocol", "select",
               ["SFTP", "FTPS", "SHARED_FOLDER", "OBJECT_STORE"]),
            _f("schedule", "Schedule"),
            _f("encryption", "Encryption"),
        ],
    },
    "BATCH": {
        "label": "Batch",
        "priority": "medium",
        "contract_format": "SCHEDULE_METADATA",
        "contract_extension": ".txt",
        "template": "batch",
        "metadata_fields": [
            _f("schedule", "Schedule"),
            _f("dependencies", "Dependencies", "list"),
            _f("sla", "SLA"),
            _f("restart_policy", "Restart policy"),
        ],
    },
}


def is_valid_type(integration_type: str) -> bool:
    return integration_type in INTEGRATION_TYPE_DEFS


def type_def(integration_type: str) -> dict:
    """Return the definition for an integration type (raises KeyError if absent)."""
    return INTEGRATION_TYPE_DEFS[integration_type]


def metadata_schema(integration_type: str) -> list[dict]:
    return list(INTEGRATION_TYPE_DEFS.get(integration_type, {}).get(
        "metadata_fields", []))


def template_name(integration_type: str) -> str:
    return INTEGRATION_TYPE_DEFS[integration_type]["template"]


def default_contract_filename(integration_type: str, integration_id: str) -> str:
    ext = INTEGRATION_TYPE_DEFS.get(integration_type, {}).get(
        "contract_extension", ".txt")
    return f"{integration_id}{ext}"


def contract_rel_path(integration_type: str, filename: str, metadata: dict) -> str:
    """Repo path of the contract file *relative to the integration directory*.

    gRPC keeps the proto under ``proto/`` (honoring an explicit ``proto_file``
    metadata value when present); other types use a flat ``contract/`` folder.
    """
    if not filename:
        return ""
    if integration_type == "GRPC":
        proto_file = (metadata or {}).get("proto_file")
        if proto_file:
            return str(proto_file)
        return f"proto/{filename}"
    return f"contract/{filename}"
