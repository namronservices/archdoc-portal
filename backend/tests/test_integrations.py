"""Phase 3 smoke test — integration documents by increment."""
from __future__ import annotations


PROTO_SAMPLE = """\
syntax = "proto3";
package fraudcheck.v1;

service FraudCheckService {
  rpc CheckTransaction (CheckRequest) returns (CheckResponse);
}

message CheckRequest { string txn_id = 1; }
message CheckResponse { bool fraud = 1; }
"""


def _scaffold(client, repo_name: str = "Payment Phase3"):
    repo_id = client.post(
        "/api/repositories", json={"name": repo_name}
    ).json()["id"]
    group_id = client.post(
        f"/api/repositories/{repo_id}/application-groups",
        json={"name": "Payments"},
    ).json()["id"]
    increment_id = client.post(
        "/api/increments",
        json={"application_group_id": group_id, "name": "MVP2"},
    ).json()["id"]
    return repo_id, increment_id


def test_grpc_integration_workflow(client):
    from app.services.git_adapter import git_adapter

    _, increment_id = _scaffold(client)

    # 1. Declare a required gRPC integration (no document yet).
    declared = client.post(
        f"/api/increments/{increment_id}/integration-docs",
        json={
            "type": "GRPC",
            "name": "Fraud Check gRPC Service",
            "source_application": "payment-platform",
            "target_application": "fraud-engine",
            "required": True,
        },
    )
    assert declared.status_code == 201, declared.text
    body = declared.json()
    assert body["document_id"] is None
    assert body["integration_id"] == "fraud-check-grpc-service"
    integration_id = body["id"]

    # 2. List shows the declared row.
    listing = client.get(f"/api/increments/{increment_id}/integration-docs")
    assert listing.status_code == 200
    assert listing.json()[0]["document_filename"] is None

    # 3. Create-missing generates the gRPC template document.
    missing = client.post(
        f"/api/increments/{increment_id}/integration-docs/create-missing"
    )
    assert missing.status_code == 200, missing.text
    assert len(missing.json()["created"]) == 1

    detail = client.get(f"/api/integrations/{integration_id}").json()
    assert detail["document_id"] is not None
    assert detail["metadata_schema"], "metadata schema should drive the UI form"
    document_id = detail["document_id"]

    # 4. Validation should flag missing metadata + missing contract.
    pre = client.post(f"/api/integrations/{integration_id}/validate").json()
    assert any("Proto contract" in r["message"] for r in pre["results"])
    assert any("Proto package" in r["message"] for r in pre["results"])

    # 5. Fill metadata.
    upd = client.put(
        f"/api/integrations/{integration_id}",
        json={
            "metadata": {
                "protocol": "HTTP_2",
                "proto_package": "fraudcheck.v1",
                "grpc_service": "FraudCheckService",
                "methods": ["CheckTransaction"],
                "streaming_type": "unary",
                "authentication": "mTLS",
                "deadline_ms": 3000,
                "retry_policy": "bounded_retry",
                "idempotency_required": True,
                "proto_file": "proto/fraudcheck/v1/fraud_check.proto",
            }
        },
    )
    assert upd.status_code == 200, upd.text

    # 6. Attach the .proto contract — text editor flow.
    contract = client.post(
        f"/api/integrations/{integration_id}/contract",
        json={"filename": "fraud_check.proto", "content": PROTO_SAMPLE},
    )
    assert contract.status_code == 200, contract.text
    assert contract.json()["path"] == "proto/fraudcheck/v1/fraud_check.proto"

    # 7. Validation now passes the high-severity checks.
    post = client.post(f"/api/integrations/{integration_id}/validate").json()
    assert not any(
        r["severity"] == "error" for r in post["results"]
    ), post["results"]

    # 8. Confirm Git layout matches the brief.
    base = "increments/mvp2/integrations/fraud-check-grpc-service"
    assert git_adapter.read_file("payment-phase3", f"{base}/integration.md")
    metadata = git_adapter.read_file("payment-phase3", f"{base}/metadata.yaml")
    assert metadata and "grpc_service: FraudCheckService" in metadata
    proto = git_adapter.read_file(
        "payment-phase3", f"{base}/proto/fraudcheck/v1/fraud_check.proto"
    )
    assert proto and "FraudCheckService" in proto

    # 9. Link the integration to the increment's HLD and confirm it surfaces.
    hld = client.post(f"/api/increments/{increment_id}/hld", json={}).json()
    linked = client.post(
        f"/api/hlds/{hld['id']}/linked-references/integrations/{integration_id}"
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["linked_integrations"][0]["integration_id"] == (
        "fraud-check-grpc-service"
    )

    # 10. Export the integration document itself.
    export = client.post(
        f"/api/documents/{document_id}/export", json={"format": "docx"}
    )
    assert export.status_code == 200, export.text
    assert export.json()["status"] in {"completed", "failed"}


def test_kafka_and_mq_templates(client):
    _, increment_id = _scaffold(client, repo_name="Payment Phase3 Mix")

    kafka = client.post(
        f"/api/increments/{increment_id}/integration-docs",
        json={
            "type": "KAFKA",
            "name": "Payment Events",
            "create_document": True,
        },
    ).json()
    mq = client.post(
        f"/api/increments/{increment_id}/integration-docs",
        json={
            "type": "MQ",
            "name": "Payment Command MQ",
            "create_document": True,
        },
    ).json()

    # Each gets its own template document with its own section set.
    kafka_doc = client.get(f"/api/hlds/{kafka['document_id']}").json()
    mq_doc = client.get(f"/api/hlds/{mq['document_id']}").json()
    assert any(s["title"] == "Topic and Event Overview" for s in kafka_doc["sections"])
    assert any(s["title"] == "Queue Overview" for s in mq_doc["sections"])

    # Type-aware validation finds the right missing fields.
    kafka_val = client.post(
        f"/api/integrations/{kafka['id']}/validate"
    ).json()
    assert any("Topic" in r["message"] for r in kafka_val["results"])
    mq_val = client.post(f"/api/integrations/{mq['id']}/validate").json()
    assert any("Queue" in r["message"] for r in mq_val["results"])
