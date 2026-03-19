from __future__ import annotations

from pathlib import Path

from seme.cli import main


def test_debug_bytecode_prints_disassembly(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "debug_bytecode.seme"
    source_file.write_text("let x = 1; print(x);", encoding="utf-8")

    code = main(["debug", "bytecode", str(source_file)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert "0000 LOAD_CONST 0 (1) ; 1:9" in captured.out
    assert "0001 DEFINE_GLOBAL 1 (x) ; 1:1" in captured.out
    assert "0003 LOAD_GLOBAL 2 (x) ; 1:18" in captured.out
    assert "0004 PRINT ; 1:17" in captured.out
    assert captured.out.rstrip().endswith("RETURN ; 1:1")


def test_debug_bytecode_returns_parse_error(tmp_path: Path, capsys) -> None:
    source_file = tmp_path / "debug_bytecode_bad.seme"
    source_file.write_text("let x = 1", encoding="utf-8")

    code = main(["debug", "bytecode", str(source_file)])
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "PARSE-001" in captured.err
