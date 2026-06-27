from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_repository_files_exist() -> None:
    required = [
        "LICENSE",
        ".github/workflows/ci.yml",
        ".github/dependabot.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CHANGELOG.md",
        "docs/architecture.md",
    ]

    for relative_path in required:
        assert (ROOT / relative_path).is_file(), relative_path


def test_pyproject_has_public_release_metadata() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["license"] == "Apache-2.0"
    assert project["urls"] == {
        "Homepage": "https://github.com/metaforismo/vo-agent",
        "Repository": "https://github.com/metaforismo/vo-agent",
        "Issues": "https://github.com/metaforismo/vo-agent/issues",
    }


def test_readme_names_license_and_public_repo() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://github.com/metaforismo/vo-agent" in readme
    assert "Apache-2.0" in readme
    assert "No open-source license has been selected" not in readme


def test_ci_runs_supported_python_versions() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "3.11" in ci
    assert "3.12" in ci
    assert "3.13" in ci
    assert "pytest -q" in ci
