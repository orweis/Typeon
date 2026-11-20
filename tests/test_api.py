import subprocess
import sys
import textwrap

import pytest

import typeon
from typeon.exceptions import TypeonException


def test_version_matches_pyproject():
    import tomllib
    from pathlib import Path

    data = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    assert data["project"]["version"] == typeon.__version__


def test_var_returns_default():
    assert typeon.var(int, 5) == 5
    assert typeon.var() is None
    assert typeon.var(str) is None


def test_typeon_class_alias():
    assert typeon.Typeon.compile is typeon.compile


def test_clean_module_imports_and_runs(fixtures_dir):
    import clean_module

    assert clean_module.run() == 6.0
    assert clean_module.Box(3).item == 3
    # functions keep the real module name and share the module's globals
    assert clean_module.run.__module__ == "clean_module"
    assert clean_module.run.__globals__ is vars(clean_module)
    # the module body ran twice (import + fuse) but is stable afterwards
    assert len(clean_module.COUNTER) == 1  # the fused re-run reset COUNTER; run() appended once


def test_broken_module_raises_on_import(fixtures_dir):
    with pytest.raises(TypeonException) as info:
        import broken_module  # noqa: F401
    assert "undefined_name" in str(info.value)


def test_nested_compile_during_fuse_is_ignored(fixtures_dir):
    # clean_module calls typeon.compile() at module level; the re-execution inside
    # that call hits compile() again, which must be a no-op (no recursion, no error).
    import clean_module

    assert clean_module.run() == 6.0


def test_compile_from_non_module_namespace_is_rejected():
    ns = {"__name__": "not_in_sys_modules", "__file__": __file__, "typeon": typeon}
    with pytest.raises(ImportError, match="not an imported module"):
        exec("typeon.compile()", ns)


def test_check_file_does_not_execute(tmp_path):
    marker = tmp_path / "ran"
    src = tmp_path / "m.py"
    src.write_text("open(%r, 'w').write('x')\n" % str(marker))
    typeon.checkFile(src)
    assert not marker.exists()


def test_check_file_reports_findings(tmp_path):
    src = tmp_path / "m.py"
    src.write_text("print(nope)\n")
    with pytest.raises(TypeonException):
        typeon.checkFile(src)


def test_script_run_as_main_reports_errors_and_main_guard_is_skipped(tmp_path):
    script = tmp_path / "prog.py"
    script.write_text(
        textwrap.dedent(
            """
            import typeon

            def f():
                return 1

            typeon.compile()

            if __name__ == "__main__":
                print("MAIN-RAN")
            """
        )
    )
    out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.count("MAIN-RAN") == 1  # not run by the re-execution inside compile()


def test_script_main_with_error_fails(tmp_path):
    script = tmp_path / "prog.py"
    script.write_text("import typeon\ntypeon.compile()\nx = undefined\n")
    out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert out.returncode != 0
    assert "TypeonException" in out.stderr and "undefined" in out.stderr
