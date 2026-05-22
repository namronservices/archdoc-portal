"""Pytest fixtures — in-memory SQLite DB and isolated Git/artifacts roots."""
from __future__ import annotations

import os
import tempfile

import pytest

# Point filesystem roots at temp dirs before any app module is imported.
_TMP = tempfile.mkdtemp(prefix="archdoc-test-")
os.environ.setdefault("GIT_DATA_ROOT", os.path.join(_TMP, "git"))
os.environ.setdefault("ARTIFACTS_ROOT", os.path.join(_TMP, "artifacts"))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_TMP, "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

_engine = create_engine(os.environ["DATABASE_URL"])
_Session = sessionmaker(bind=_engine)
Base.metadata.create_all(_engine)


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app)
