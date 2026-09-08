# Public GitHub Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare Limes Quaestio for public GitHub release, create `metaforismo/limes-quaestio`, and push a verified `main` branch.

**Architecture:** Add public repository hygiene files and CI while preserving the local-first Python package. Keep generated runtime artifacts ignored, add explicit license/package metadata, validate the repo with tests, then create and push the public GitHub repository through `gh`.

**Tech Stack:** Python 3.11+, pytest, uv, GitHub Actions, git, GitHub CLI.

---

## File Structure

- Create: `LICENSE`
  - Apache-2.0 license chosen for a public agent-runtime library with patent grant.
- Create: `.github/workflows/ci.yml`
  - Runs tests on Python 3.11, 3.12, and 3.13.
- Create: `.github/dependabot.yml`
  - Checks GitHub Actions weekly.
- Create: `.github/pull_request_template.md`
  - Standard summary and test plan prompt.
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
  - Structured bug reports.
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
  - Structured feature requests.
- Modify: `pyproject.toml`
  - Add Apache-2.0 license metadata and real project URLs.
- Modify: `README.md`
  - Replace repository-status note with public repository and license sections.
- Modify: `SECURITY.md`
  - Add GitHub Security Advisories reporting path.
- Create: `tests/test_repository_hygiene.py`
  - Tests public-release metadata and required repository files.

## Executable Checklist

- [x] Confirm local git status before edits.
- [x] Confirm GitHub auth and account.
- [x] Confirm `metaforismo/limes-quaestio` is available.
- [x] Write failing repository hygiene tests.
- [x] Run focused hygiene tests and confirm failures.
- [x] Add Apache-2.0 `LICENSE`.
- [x] Add GitHub Actions CI workflow.
- [x] Add Dependabot config.
- [x] Add pull request template.
- [x] Add bug report issue template.
- [x] Add feature request issue template.
- [x] Update `pyproject.toml` license metadata.
- [x] Update `pyproject.toml` URLs for `metaforismo/limes-quaestio`.
- [x] Update README public repository and license sections.
- [x] Update SECURITY with GitHub private vulnerability reporting.
- [x] Run focused hygiene tests.
- [x] Run full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Run `uv build`.
- [x] Clean generated build/test artifacts.
- [x] Commit public-release setup locally.
- [x] Create public GitHub repository `metaforismo/limes-quaestio`.
- [x] Push `main` to GitHub and set upstream.
- [x] Verify remote repository visibility and URL.
- [x] Verify local git status is clean.
- [x] Update this plan with verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_repository_hygiene.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
for example in examples/*.py; do UV_PROJECT_ENVIRONMENT=work/.venv uv run python "$example"; done
for bundle in work/*-bundle.json; do UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate "$bundle"; done
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
UV_PROJECT_ENVIRONMENT=work/.venv uv build
gh repo create limes-quaestio --public --source . --remote origin --push
gh repo view metaforismo/limes-quaestio --json nameWithOwner,visibility,url
git status --short
```

## Self-Review

- Spec coverage: includes public repo creation, public metadata, CI, templates, license, tests, push, and verification.
- Placeholder scan: no TODO or TBD placeholders.
- Type consistency: repository name is consistently `limes-quaestio`, owner is `metaforismo`, package name remains `limes-quaestio`.

## Verification Evidence

- Red phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_repository_hygiene.py -q` failed with 4 expected failures before release files existed.
- Focused hygiene: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_repository_hygiene.py -q` -> `4 passed in 0.00s`.
- Full tests: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q` -> `144 passed in 3.43s`.
- Examples: `for example in examples/*.py; do UV_PROJECT_ENVIRONMENT=work/.venv uv run python "$example"; done` generated all example bundles and reports.
- Bundle validation: `for bundle in work/*-bundle.json; do UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate "$bundle"; done` validated 11 bundles.
- Compile: `UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples` passed.
- Smoke: package import plus `pyproject.toml` URL/license checks printed `public release smoke ok`.
- Build: `UV_PROJECT_ENVIRONMENT=work/.venv uv build` built `dist/vo_agent-0.1.0.tar.gz` and `dist/vo_agent-0.1.0-py3-none-any.whl`.
- Local release commit: `git commit -m "Prepare public GitHub release"` -> `4c5eac9`.
- Remote creation: `gh repo create limes-quaestio --public --source . --remote origin --push --description "Evidence-gated workflows for coordinating coding agents."` -> `https://github.com/Limes-Labs/limes-quaestio`.
- Remote verification: `gh repo view metaforismo/limes-quaestio --json nameWithOwner,visibility,url --jq '{nameWithOwner,visibility,url}'` -> `{"nameWithOwner":"metaforismo/limes-quaestio","url":"https://github.com/Limes-Labs/limes-quaestio","visibility":"PUBLIC"}`.
- Workflow verification: `gh workflow list -R metaforismo/limes-quaestio` showed active `CI` and `Dependabot Updates` workflows.
