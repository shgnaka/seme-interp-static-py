from __future__ import annotations

from pathlib import Path

from seme.cli import main


def test_run_success_returns_zero_and_prints_stdout(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "ok_run.seme"
    source_file.write_text("print(1); print(true);", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.out == "1\ntrue\n"
    assert captured.err == ""


def test_run_type_error_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_type_run.seme"
    source_file.write_text("if (1) { print(1); }", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "TYPE-007" in captured.err


def test_run_parse_error_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_parse_run.seme"
    source_file.write_text("let x = 1", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "PARSE-001" in captured.err


def test_run_runtime_error_keeps_partial_stdout(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_runtime_run.seme"
    source_file.write_text("print(1); let x = 1 / 0; print(x);", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == "1\n"
    assert "RUNTIME-001" in captured.err
