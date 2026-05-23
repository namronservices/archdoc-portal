"""Phase 4 smoke test — Enterprise Repository + Dashboard + start-increment."""
from __future__ import annotations


def test_sync_and_dashboard(client):
    sync = client.post("/api/enterprise/sync")
    assert sync.status_code == 200, sync.text
    counts = sync.json()["counts"]
    # Seed includes 2 domains, 2 capabilities, 4 applications, 1 app-group, etc.
    assert counts.get("business/domains") == 2
    assert counts.get("business/capabilities") == 2
    assert counts.get("application/applications") == 4
    assert counts.get("application/application-groups") == 1

    dashboard = client.get("/api/enterprise/dashboard").json()
    payments = next(
        d for d in dashboard["business"]["domains"] if d["slug"] == "payments"
    )
    assert payments["capability_count"] == 2
    assert payments["application_count"] == 4

    pm = next(
        g
        for g in dashboard["application"]["application_groups"]
        if g["slug"] == "payment-modernization"
    )
    assert pm["application_count"] == 4
    assert pm["increment_count"] == 0


def test_start_increment_creates_hld_with_chain(client):
    # Ensure the enterprise repo + DB rows are synced.
    client.post("/api/enterprise/sync")

    started = client.post(
        "/api/enterprise/application-groups/payment-modernization/start-increment",
        json={"increment_name": "MVP2", "hld_title": "Payment Platform HLD"},
    )
    assert started.status_code == 201, started.text
    body = started.json()
    increment_id = body["increment_id"]
    hld_id = body["hld_id"]

    context = client.get(f"/api/hlds/{hld_id}/architecture-context").json()
    chain_types = [c["object_type"] for c in context["chain"]]
    assert chain_types == [
        "domain",
        "application_group",
        "architecture_increment",
        "hld",
    ]
    # Domain is auto-linked from the group's domain_slug.
    domain_row = next(
        c for c in context["chain"] if c["object_type"] == "domain"
    )
    assert domain_row["object_slug"] == "payments"
    assert domain_row["label"] == "Payments"

    # Layered view exposes the same links per architectural layer.
    layers = {layer["layer"]: layer["rows"] for layer in context["layers"]}
    assert any(
        r["object_slug"] == "payments" for r in layers["Business Layer"]
    )

    # Adding a capability link via the slug endpoint.
    add = client.post(
        f"/api/hlds/{hld_id}/links/capability/payment-initiation"
    )
    assert add.status_code == 200, add.text
    assert any(
        r["object_type"] == "capability"
        and r["object_slug"] == "payment-initiation"
        for r in add.json()["layers"][0]["rows"]
    )

    # Dashboard now reports the increment + HLD against the group.
    dashboard = client.get("/api/enterprise/dashboard").json()
    pm = next(
        g
        for g in dashboard["application"]["application_groups"]
        if g["slug"] == "payment-modernization"
    )
    assert pm["increment_count"] == 1
    assert pm["hld_count"] == 1
    assert pm["recent_increments"][0]["hld_id"] == hld_id

    # Increment-integration endpoint still works against the auto-provisioned repo.
    integrations = client.get(
        f"/api/increments/{increment_id}/integration-docs"
    )
    assert integrations.status_code == 200, integrations.text


def test_create_domain_writes_yaml_to_git(client):
    from app.services.git_adapter import git_adapter

    client.post("/api/enterprise/sync")

    created = client.post(
        "/api/enterprise/domains",
        json={
            "name": "Cards",
            "owner": "business-architecture",
            "archimate_type": "grouping",
            "description": "Card issuing and acquiring.",
        },
    )
    assert created.status_code == 201, created.text
    yaml_text = git_adapter.read_file(
        "enterprise-repository", "business/domains/cards.yaml"
    )
    assert yaml_text and "domain_id: cards" in yaml_text
