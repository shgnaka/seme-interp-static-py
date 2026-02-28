from __future__ import annotations

from io import StringIO

from seme.cli import repl_loop


def test_repl_persistent_scope_across_lines() -> None:
    inp = StringIO("let x = 1;\nx = x + 1;\nprint(x);\n:quit\n")
    out = StringIO()
    err = StringIO()

    code = repl_loop(inp, out, err)

    assert code == 0
    assert "2\n" in out.getvalue()
    assert err.getvalue() == ""


def test_repl_typecheck_gates_execution() -> None:
    inp = StringIO("if (1) { print(1); }\n:quit\n")
    out = StringIO()
    err = StringIO()

    code = repl_loop(inp, out, err)

    assert code == 0
    assert "1\n" not in out.getvalue()
    assert "TYPE-007" in err.getvalue()


def test_repl_quit_command() -> None:
    inp = StringIO(":quit\n")
    out = StringIO()
    err = StringIO()

    code = repl_loop(inp, out, err)

    assert code == 0
    assert err.getvalue() == ""


def test_repl_eof_exits_zero() -> None:
    inp = StringIO("")
    out = StringIO()
    err = StringIO()

    code = repl_loop(inp, out, err)

    assert code == 0
    assert out.getvalue().endswith("\n")
    assert err.getvalue() == ""


def test_repl_runtime_error_does_not_corrupt_session_state() -> None:
    inp = StringIO("let x = 1;\n{ x = 99; let z = 1 / 0; }\nprint(x);\n:quit\n")
    out = StringIO()
    err = StringIO()

    code = repl_loop(inp, out, err)

    assert code == 0
    assert "RUNTIME-001" in err.getvalue()
    assert out.getvalue().count("1\n") == 1
    assert "99\n" not in out.getvalue()
