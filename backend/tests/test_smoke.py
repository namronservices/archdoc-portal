"""End-to-end smoke test covering the Phase 1 vertical slice."""
from __future__ import annotations


def test_full_hld_workflow(client):
    # 1. Repository
    repo = client.post("/api/repositories", json={"name": "Payment Modernization"})
    assert repo.status_code == 201, repo.text
    repo_id = repo.json()["id"]

    # 2. Application group
    group = client.post(
        f"/api/repositories/{repo_id}/application-groups",
        json={"name": "Payments"},
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    # 3. Increment
    increment = client.post(
        "/api/increments",
        json={"application_group_id": group_id, "name": "MVP2"},
    )
    assert increment.status_code == 201, increment.text
    increment_id = increment.json()["id"]

    # 4. HLD from template — 9 chapters + 3 sub-chapters = 12 sections.
    hld = client.post(f"/api/increments/{increment_id}/hld", json={})
    assert hld.status_code == 201, hld.text
    doc = hld.json()
    doc_id = doc["id"]
    assert len(doc["sections"]) == 12
    assert doc["head_commit"]
    assert doc["breadcrumb"]["increment"] == "MVP2"

    # 5. Edit a section
    first_section = doc["sections"][0]["id"]
    upd = client.put(
        f"/api/hlds/{doc_id}/sections/{first_section}",
        json={"content": "Edited summary."},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["content"] == "Edited summary."

    # 6. Add a custom chapter + sub-chapter
    chap = client.post(f"/api/hlds/{doc_id}/chapters", json={"title": "Appendix"})
    assert chap.status_code == 200, chap.text
    custom = next(s for s in chap.json()["sections"] if s["title"] == "Appendix")
    assert custom["kind"] == "custom"

    sub = client.post(
        f"/api/hlds/{doc_id}/subchapters",
        json={"parent_id": custom["id"], "title": "Glossary"},
    )
    assert sub.status_code == 200, sub.text
    glossary = next(s for s in sub.json()["sections"] if s["title"] == "Glossary")
    assert glossary["number"].startswith(custom["number"] + ".")

    # 7. Diagram lifecycle (render result depends on mmdc availability).
    diagram = client.post(
        f"/api/hlds/{doc_id}/diagrams",
        json={"section_id": first_section, "name": "system-context"},
    )
    assert diagram.status_code == 201, diagram.text
    diagram_id = diagram.json()["id"]

    put = client.put(
        f"/api/diagrams/{diagram_id}",
        json={"source": "graph TD\n A-->B"},
    )
    assert put.status_code == 200, put.text

    render = client.post(f"/api/diagrams/{diagram_id}/render")
    assert render.status_code == 200, render.text
    assert render.json()["render_status"] in {"rendered", "error"}

    # 8. Save to Git
    save = client.post(f"/api/documents/{doc_id}/save")
    assert save.status_code == 200, save.text
    assert save.json()["short_hash"]

    # 9. Validation
    validation = client.get(f"/api/documents/{doc_id}/validation")
    assert validation.status_code == 200, validation.text
    assert "results" in validation.json()

    # 10. Export (status depends on pandoc availability).
    export = client.post(
        f"/api/documents/{doc_id}/export", json={"format": "docx"}
    )
    assert export.status_code == 200, export.text
    assert export.json()["status"] in {"completed", "failed"}


def test_reuse_blocks_workflow(client):
    """Phase 2: browse the library, insert linked/snapshot/forked reuse, save."""
    from app.services.git_adapter import git_adapter

    # Library is seeded on first list.
    blocks = client.get("/api/reusable-blocks")
    assert blocks.status_code == 200, blocks.text
    library = blocks.json()
    assert len(library) >= 6
    block_id = "security-oauth2-client-credentials"
    assert any(b["block_id"] == block_id for b in library)

    # Single block fetch + category filter.
    one = client.get(f"/api/reusable-blocks/{block_id}")
    assert one.status_code == 200, one.text
    assert one.json()["status"] == "approved"
    assert client.get("/api/reusable-blocks?category=security").json()

    # Project scaffolding.
    repo_id = client.post(
        "/api/repositories", json={"name": "Reuse Demo"}
    ).json()["id"]
    group_id = client.post(
        f"/api/repositories/{repo_id}/application-groups",
        json={"name": "Payments"},
    ).json()["id"]
    increment_id = client.post(
        "/api/increments",
        json={"application_group_id": group_id, "name": "Reuse MVP"},
    ).json()["id"]
    doc = client.post(f"/api/increments/{increment_id}/hld", json={}).json()
    doc_id = doc["id"]
    section_id = doc["sections"][0]["id"]

    # Insert linked.
    linked = client.post(
        f"/api/hlds/{doc_id}/reuse/{block_id}/insert-linked",
        json={"section_id": section_id},
    )
    assert linked.status_code == 200, linked.text
    assert len(linked.json()["reuse_instances"]) == 1
    assert linked.json()["reuse_instances"][0]["reuse_mode"] == "linked"

    # Insert snapshot.
    snap = client.post(
        f"/api/hlds/{doc_id}/reuse/nfr-idempotency/insert-snapshot",
        json={"section_id": section_id},
    )
    assert snap.status_code == 200, snap.text
    snap_inst = next(
        i for i in snap.json()["reuse_instances"] if i["reuse_mode"] == "snapshot"
    )
    assert "idempotent" in snap_inst["body"].lower()

    # Fork & edit.
    forked = client.post(
        f"/api/hlds/{doc_id}/reuse/{block_id}/fork",
        json={"section_id": section_id, "title": "OAuth2 — Payment Variant"},
    )
    assert forked.status_code == 200, forked.text
    fork_inst = next(
        i for i in forked.json()["reuse_instances"] if i["reuse_mode"] == "forked"
    )
    assert fork_inst["derived_block_id"]

    edit = client.put(
        f"/api/hlds/{doc_id}/reuse/{fork_inst['id']}",
        json={"body": "## Variant\n\nCustomized for payments.", "rationale": "Adds payment scope."},
    )
    assert edit.status_code == 200, edit.text
    assert "Customized for payments" in edit.json()["body"]
    assert edit.json()["rationale"] == "Adds payment scope."

    # Save → reuse persisted to Git.
    save = client.post(f"/api/documents/{doc_id}/save")
    assert save.status_code == 200, save.text
    base = f"increments/reuse-mvp/hld"
    reuse_yaml = git_adapter.read_file("reuse-demo", f"{base}/reuse-instances.yaml")
    assert reuse_yaml and "reuse_mode: linked" in reuse_yaml
    fork_file = git_adapter.read_file(
        "reuse-demo", f"{base}/forked-blocks/{fork_inst['derived_block_id']}.md"
    )
    assert fork_file and "Customized for payments" in fork_file
    hld_md = git_adapter.read_file("reuse-demo", f"{base}/hld.md")
    assert "{{reuse:security/oauth2-client-credentials@1.2}}" in hld_md

    # Validation surfaces the rationale-less / unapproved checks (fork now has one).
    validation = client.get(f"/api/documents/{doc_id}/validation")
    assert validation.status_code == 200, validation.text

    # Export resolves reuse content.
    export = client.post(
        f"/api/documents/{doc_id}/export", json={"format": "docx"}
    )
    assert export.status_code == 200, export.text
    assert export.json()["status"] in {"completed", "failed"}
