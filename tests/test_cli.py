from __future__ import annotations

import json

from vo import WorkflowRun
from vo.cli import main


def test_cli_validate_reports_valid_bundle(tmp_path, capsys) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(WorkflowRun(name="cli validate").to_dict()), encoding="utf-8")

    exit_code = main(["validate", str(path)])

    assert exit_code == 0
    assert "valid: cli validate" in capsys.readouterr().out


def test_cli_inspect_prints_markdown_report(tmp_path, capsys) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(WorkflowRun(name="cli inspect").to_dict()), encoding="utf-8")

    exit_code = main(["inspect", str(path)])

    assert exit_code == 0
    assert "# cli inspect" in capsys.readouterr().out


def test_cli_validate_returns_failure_for_invalid_bundle(tmp_path, capsys) -> None:
    path = tmp_path / "bundle.json"
    path.write_text("{}", encoding="utf-8")

    exit_code = main(["validate", str(path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "invalid:" in captured.err
