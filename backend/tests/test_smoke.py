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
