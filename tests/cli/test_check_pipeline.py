from __future__ import annotations

from pathlib import Path

from seme.cli import main


def test_check_success_returns_zero(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "ok.seme"
    source_file.write_text("let x = 1; x = x + 1;", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""


def test_check_parse_error_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_parse.seme"
    source_file.write_text("let x = 1", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "PARSE-001" in captured.err


def test_check_type_error_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_type.seme"
    source_file.write_text("if (1) { let x = 1; }", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "TYPE-007" in captured.err


def test_parse_error_blocks_typecheck(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "parse_before_type.seme"
    source_file.write_text("let x = 1\nif (1) { let y = 2; }", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "PARSE-001" in captured.err
    assert "TYPE-" not in captured.err


def test_check_lex_error_returns_one(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "bad_lex.seme"
    source_file.write_text("@", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "LEX-001" in captured.err
