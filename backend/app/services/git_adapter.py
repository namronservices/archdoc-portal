"""Git adapter — hides Git complexity behind a small read/write/commit API.

Each repository is a local **bare** repo at ``<git_data_root>/<slug>.git``.
The adapter keeps a single working checkout at ``<git_data_root>/work/<slug>``
where files are materialised, committed, and pushed back to the bare repo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from git import Actor, Repo

from app.config import settings

DEFAULT_BRANCH = "main"


@dataclass
class CommitInfo:
    """Metadata about a commit, surfaced to the UI."""

    hash: str
    short_hash: str
    message: str
    author: str
    committed_at: str  # ISO 8601


class GitError(RuntimeError):
    """Raised when a Git operation fails."""


class GitAdapter:
    """Manages bare repos and their working checkouts under the data root."""

    def __init__(self, data_root: str | None = None) -> None:
        self.data_root = Path(data_root or settings.git_data_root)
        self.work_root = self.data_root / "work"
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._actor = Actor(settings.git_author_name, settings.git_author_email)

    # -- paths -------------------------------------------------------------
    def bare_path(self, slug: str) -> Path:
        return self.data_root / f"{slug}.git"

    def work_path(self, slug: str) -> Path:
        return self.work_root / slug

    # -- lifecycle ---------------------------------------------------------
    def init_repository(self, slug: str) -> str:
        """Create a bare repo + working checkout with an empty initial commit.

        Returns the absolute bare-repo path (stored on the Repository row).
        Idempotent: a no-op if the repo already exists.
        """
        bare = self.bare_path(slug)
        if bare.exists():
            return str(bare)

        Repo.init(bare, bare=True, initial_branch=DEFAULT_BRANCH)

        work = self.work_path(slug)
        repo = Repo.clone_from(str(bare), str(work))
        # Empty bare repo -> clone has no branch yet; create the initial commit.
        gitkeep = work / ".gitkeep"
        gitkeep.write_text("")
        repo.index.add([".gitkeep"])
        repo.index.commit(
            "Initialize repository", author=self._actor, committer=self._actor
        )
        self._push(repo)
        return str(bare)

    def _ensure_work(self, slug: str) -> Repo:
        """Return the working-checkout Repo, cloning it if missing."""
        work = self.work_path(slug)
        if (work / ".git").exists():
            return Repo(str(work))
        bare = self.bare_path(slug)
        if not bare.exists():
            raise GitError(f"Repository '{slug}' has not been initialized")
        return Repo.clone_from(str(bare), str(work))

    def _push(self, repo: Repo) -> None:
        repo.remote("origin").push(DEFAULT_BRANCH)

    # -- read / write ------------------------------------------------------
    def read_file(self, slug: str, rel_path: str) -> str | None:
        path = self.work_path(slug) / rel_path
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write_files(self, slug: str, files: dict[str, str]) -> None:
        """Write a batch of text files (relative paths) into the working tree."""
        work = self.work_path(slug)
        for rel_path, content in files.items():
            target = work / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def write_binary(self, slug: str, rel_path: str, data: bytes) -> None:
        target = self.work_path(slug) / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    # -- commit ------------------------------------------------------------
    def commit(self, slug: str, files: dict[str, str], message: str) -> CommitInfo:
        """Write ``files``, stage everything, commit, and push to the bare repo."""
        repo = self._ensure_work(slug)
        self.write_files(slug, files)
        repo.git.add(A=True)
        if not repo.is_dirty(untracked_files=True) and not repo.index.diff("HEAD"):
            # Nothing changed — still return current head metadata.
            return self.head_info(slug)
        commit = repo.index.commit(
            message, author=self._actor, committer=self._actor
        )
        self._push(repo)
        return self._to_info(commit)

    def head_info(self, slug: str) -> CommitInfo:
        repo = self._ensure_work(slug)
        return self._to_info(repo.head.commit)

    @staticmethod
    def _to_info(commit) -> CommitInfo:
        return CommitInfo(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:8],
            message=commit.message.strip(),
            author=str(commit.author),
            committed_at=commit.committed_datetime.isoformat(),
        )

    def abs_work_path(self, slug: str, rel_path: str = "") -> str:
        return os.path.join(str(self.work_path(slug)), rel_path)


# Module-level singleton used by services and routers.
git_adapter = GitAdapter()
