# ArchDoc Portal — Phase 1

Open-source, Git-backed architecture authoring portal. Phase 1 delivers the core
vertical slice: create an architecture increment, generate an HLD from a
template, edit chapters in a focused editor, add Mermaid diagrams, save canonical
source to Git, and export DOCX/PDF.

## Stack

- **Backend** — FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend** — React + Vite + TypeScript, Tailwind, Milkdown, CodeMirror 6
- **Source storage** — local bare Git repositories (Git complexity hidden)
- **Export** — Pandoc + Mermaid CLI (DOCX + PDF)

## Run

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000/docs

### "This site can't be reached" (Colima users)

Colima tunnels container ports to `localhost` automatically, but its watcher
can miss newly published ports. If the site won't load, add the forwards:

```bash
./scripts/colima-port-forward.sh
```

The forwards last for the life of the Colima VM (re-run after `colima restart`
or a reboot). Docker Desktop / OrbStack users do not need this.

### Adding a frontend dependency

The `frontend` service keeps `node_modules` in an anonymous volume
(`docker-compose.yml`), so it is **not** updated by a host-side `npm install`
or by `docker compose up --build` (the volume shadows the rebuilt image). After
changing `frontend/package.json`, install into the running container:

```bash
docker compose exec frontend npm install
docker compose restart frontend
```

## Layout

```
backend/    FastAPI app, Git adapter, template/mermaid/export services
frontend/   React HLD editor (3-panel layout)
git-data/   bare repos + working checkouts (Docker volume)
artifacts/  export outputs (Docker volume)
```

## Workflow

```
create repository + application group
  → create architecture increment
  → create HLD from template
  → edit sections / add custom chapters
  → add Mermaid diagram blocks
  → Save  (commits Markdown/YAML/Mermaid to Git)
  → Export (DOCX/PDF via Pandoc)
```

See `backend/README.md` and the Phase 1 spec for details.
