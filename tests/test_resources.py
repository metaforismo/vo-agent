import pytest

from quaestio import ResourceConflict, ResourceManager


def test_resource_manager_blocks_conflicting_active_lease():
    resources = ResourceManager()
    lease = resources.acquire("repo:src/parser.py", owner="optimizer")

    with pytest.raises(ResourceConflict):
        resources.acquire("repo:src/parser.py", owner="reviewer")

    lease.release()
    second = resources.acquire("repo:src/parser.py", owner="reviewer")

    assert second.owner == "reviewer"
    assert resources.snapshot()["repo:src/parser.py"]["owner"] == "reviewer"
