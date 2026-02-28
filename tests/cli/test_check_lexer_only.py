from __future__ import annotations

from pathlib import Path

from seme.cli import main


def test_check_success_returns_zero(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "ok.seme"
    source_file.write_text("let x = 1;", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""


def test_check_invalid_token_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad.seme"
    source_file.write_text("@", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "LEX-001 1:1" in captured.err
