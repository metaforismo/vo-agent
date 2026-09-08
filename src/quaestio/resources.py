"""Explicit resource leases for shared workflow state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from quaestio.exceptions import ResourceConflict
from quaestio.models import short_id, utc_now

if TYPE_CHECKING:
    from collections.abc import MutableMapping


@dataclass(slots=True)
class ResourceLease:
    """A live lease on a named resource."""

    name: str
    owner: str
    token: str = field(default_factory=short_id)
    acquired_at: str = field(default_factory=utc_now)
    _leases: "MutableMapping[str, ResourceLease] | None" = field(
        default=None, repr=False, compare=False
    )

    @property
    def active(self) -> bool:
        return self._leases is not None and self._leases.get(self.name) is self

    def release(self) -> None:
        if self._leases is not None and self._leases.get(self.name) is self:
            self._leases.pop(self.name, None)
        self._leases = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "owner": self.owner,
            "token": self.token,
            "acquired_at": self.acquired_at,
            "active": self.active,
        }


class ResourceManager:
    """Tracks active resource leases by name."""

    def __init__(self) -> None:
        self._leases: dict[str, ResourceLease] = {}

    def acquire(self, name: str, *, owner: str) -> ResourceLease:
        if not name.strip():
            raise ValueError("resource name must not be empty")
        if not owner.strip():
            raise ValueError("resource owner must not be empty")

        existing = self._leases.get(name)
        if existing is not None:
            if existing.owner == owner:
                return existing
            raise ResourceConflict(
                f"resource {name!r} is already leased by {existing.owner!r}"
            )

        lease = ResourceLease(name=name, owner=owner, _leases=self._leases)
        self._leases[name] = lease
        return lease

    def release(self, name: str, *, owner: str | None = None) -> None:
        lease = self._leases.get(name)
        if lease is None:
            return
        if owner is not None and lease.owner != owner:
            raise ResourceConflict(
                f"resource {name!r} is leased by {lease.owner!r}, not {owner!r}"
            )
        lease.release()

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {name: lease.to_dict() for name, lease in sorted(self._leases.items())}
