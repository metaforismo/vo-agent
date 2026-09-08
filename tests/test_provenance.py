from pathlib import Path

from quaestio import collect_provenance


def test_collect_provenance_records_runtime_and_selected_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VO_TEST_ENV", "visible")
    monkeypatch.setenv("VO_SECRET_ENV", "hidden")

    provenance = collect_provenance(
        cwd=tmp_path,
        argv=["quaestio", "run"],
        env_keys=["VO_TEST_ENV"],
    )

    assert provenance.cwd == str(tmp_path)
    assert provenance.argv == ["quaestio", "run"]
    assert provenance.env == {"VO_TEST_ENV": "visible"}
    assert "VO_SECRET_ENV" not in provenance.env
    assert provenance.python_version
    assert provenance.platform
    assert provenance.git is None
