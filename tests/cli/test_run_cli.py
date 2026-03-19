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


def test_run_const_requires_initializer_returns_parse_error(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "const_no_init_run.seme"
    source_file.write_text("const x: int;", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "PARSE-001 1:13" in captured.err
    assert "Expected '=' and initializer in const declaration" in captured.err


def test_run_print_in_value_context_returns_type008(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "print_expr_ctx_run.seme"
    source_file.write_text("print(1) == print(2);", encoding="utf-8")

    code = main(["run", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "TYPE-008 1:6 print(expr) can only appear as a statement" in captured.err
    assert "TYPE-008 1:18 print(expr) can only appear as a statement" in captured.err


def test_run_backend_interpreter_is_available_for_reference(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "run_interpreter_backend.seme"
    source_file.write_text("let x = 1; x = x + 2; print(x);", encoding="utf-8")

    code = main(["run", "--backend", "interpreter", str(source_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.out == "3\n"
    assert captured.err == ""
