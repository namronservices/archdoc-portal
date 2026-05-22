# ArchDoc Portal — Backend

FastAPI service for HLD authoring, Git-backed source storage, and export.

## Layout

```
app/
  main.py            FastAPI app + router wiring
  config.py          env-driven settings
  db.py              SQLAlchemy engine/session
  models.py          ORM models (operational metadata only)
  schemas.py         Pydantic request/response models
  views.py           shared response builders
  routers/           repositories, increments, hld, diagrams, documents
  services/
    git_adapter.py   bare repos + working checkouts (read/write/commit)
    template.py      HLD template -> document sections
    serializer.py    document -> canonical Git file set
    numbering.py     section ordering + numbering
    mermaid.py       mmdc render wrapper
    export.py        Pandoc DOCX/PDF export
  templates/hld_template.yaml
alembic/             migrations
tests/               end-to-end smoke test
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Mermaid/Pandoc export needs mmdc + pandoc on PATH (provided by the Docker image).
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest        # SQLite-backed smoke test of the full Phase 1 flow
```

Diagram rendering and export degrade gracefully when `mmdc` / `pandoc` are
absent, so the smoke test passes without them installed.

## Notes

- No authentication in Phase 1; Git commits use a fixed author from settings.
- Section content lives in PostgreSQL while editing; canonical Markdown/YAML/
  Mermaid is written to Git on an explicit Save.
- On macOS, Docker bind-mount file events may not reach `uvicorn --reload`;
  restart the `backend` container to pick up code changes.
