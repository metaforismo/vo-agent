"""Artifact provenance for workflow bundles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vo.models import jsonable, utc_now


@dataclass(slots=True)
class Artifact:
    """Metadata for a local file produced by a workflow."""

    path: str
    kind: str
    sha256: str
    size_bytes: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "metadata": jsonable(self.metadata),
            "created_at": self.created_at,
        }


class ArtifactStore:
    """In-memory registry for local workflow artifacts."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else None
        self._artifacts: list[Artifact] = []

    def register(
        self,
        path: str | Path,
        *,
        kind: str = "file",
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))
        if not file_path.is_file():
            raise ValueError(f"artifact path is not a file: {file_path}")

        resolved = file_path.resolve()
        content = resolved.read_bytes()
        artifact = Artifact(
            path=self._display_path(resolved),
            kind=kind,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            metadata=dict(metadata or {}),
        )
        self._artifacts.append(artifact)
        return artifact

    def to_list(self) -> list[dict[str, Any]]:
        return [artifact.to_dict() for artifact in self._artifacts]

    def _display_path(self, path: Path) -> str:
        if self.root is None:
            return str(path)
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)
