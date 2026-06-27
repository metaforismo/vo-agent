"""Run provenance capture for reproducible workflow bundles."""

from __future__ import annotations

import os
import platform as platform_module
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from vo.models import jsonable, utc_now


@dataclass(slots=True)
class GitInfo:
    """Best-effort git state for a run working directory."""

    root: str
    commit: str
    branch: str
    dirty: bool
    changed_files: int
    untracked_files: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "commit": self.commit,
            "branch": self.branch,
            "dirty": self.dirty,
            "changed_files": self.changed_files,
            "untracked_files": self.untracked_files,
        }


@dataclass(slots=True)
class RunProvenance:
    """Local environment metadata for a workflow run."""

    cwd: str
    argv: list[str]
    python_version: str
    python_executable: str
    platform: str
    env: dict[str, str]
    git: GitInfo | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cwd": self.cwd,
            "argv": list(self.argv),
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "platform": self.platform,
            "env": jsonable(self.env),
            "git": self.git.to_dict() if self.git else None,
            "created_at": self.created_at,
        }


def collect_provenance(
    *,
    cwd: str | Path | None = None,
    argv: list[str] | None = None,
    env_keys: Sequence[str] = (),
) -> RunProvenance:
    """Collect local run provenance without sweeping in the whole environment."""

    resolved_cwd = Path(cwd).resolve() if cwd is not None else Path.cwd().resolve()
    selected_env = {key: os.environ[key] for key in env_keys if key in os.environ}
    return RunProvenance(
        cwd=str(resolved_cwd),
        argv=list(sys.argv if argv is None else argv),
        python_version=platform_module.python_version(),
        python_executable=sys.executable,
        platform=platform_module.platform(),
        env=selected_env,
        git=_collect_git_info(resolved_cwd),
        created_at=utc_now(),
    )


def _collect_git_info(cwd: Path) -> GitInfo | None:
    root = _git(cwd, "rev-parse", "--show-toplevel")
    commit = _git(cwd, "rev-parse", "HEAD")
    if root is None or commit is None:
        return None

    branch = _git(cwd, "branch", "--show-current") or ""
    status = _git(cwd, "status", "--porcelain") or ""
    changed = 0
    untracked = 0
    for line in status.splitlines():
        if line.startswith("??"):
            untracked += 1
        elif line.strip():
            changed += 1

    return GitInfo(
        root=root,
        commit=commit,
        branch=branch,
        dirty=bool(status.strip()),
        changed_files=changed,
        untracked_files=untracked,
    )


def _git(cwd: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()
