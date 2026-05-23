"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    diagrams,
    documents,
    hld,
    increments,
    integrations,
    repositories,
    reusable_blocks,
    reuse,
)

app = FastAPI(title="ArchDoc Portal API", version="0.1.0")

# Phase 1 has no auth; allow the local frontend dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories.router)
app.include_router(increments.router)
app.include_router(hld.router)
app.include_router(integrations.router)
app.include_router(diagrams.router)
app.include_router(documents.router)
app.include_router(reusable_blocks.router)
app.include_router(reuse.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
