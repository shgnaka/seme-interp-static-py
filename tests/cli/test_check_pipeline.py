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


def test_check_const_requires_initializer_returns_parse_error(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "const_no_init.seme"
    source_file.write_text("const x: int;", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "PARSE-001 1:13" in captured.err
    assert "Expected '=' and initializer in const declaration" in captured.err


def test_check_print_in_value_context_returns_type008(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "print_expr_ctx.seme"
    source_file.write_text("print(1) == print(2);", encoding="utf-8")

    code = main(["check", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert "TYPE-008 1:6 print(expr) can only appear as a statement" in captured.err
    assert "TYPE-008 1:18 print(expr) can only appear as a statement" in captured.err
