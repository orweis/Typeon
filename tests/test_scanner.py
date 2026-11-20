import textwrap

import pytest

import typeon
from typeon import scanner
from typeon.exceptions import TypeonException


def errors_of(source):
    """Return the repr() of every finding for ``source`` (never raises on findings)."""
    typer = scanner.TypeonTyper(throw=False)
    typer.handleModuleSource(textwrap.dedent(source))
    return [repr(e) for e in sorted(typer._errors, key=lambda e: e.position)]


def check(source):
    return typeon.checkSource(textwrap.dedent(source))


class TestNames:
    def test_clean_code_passes(self):
        assert (
            errors_of("""
            import os
            from os import path as p
            x = 1
            def f(a, *args, k=2, **kw):
                return a + x + k + len(args) + len(kw) + len(os.sep) + len(p.sep)
            """)
            == []
        )

    def test_undefined_name_is_reported_with_position(self):
        errs = errors_of("x = 1\ny = missing\n")
        assert len(errs) == 1
        assert "'missing'" in errs[0] and "line:2 col:4" in errs[0]

    def test_function_may_use_name_defined_later(self):
        assert (
            errors_of("""
            def f():
                return g()
            def g():
                return LATER
            LATER = 1
            """)
            == []
        )

    def test_module_level_use_before_definition_is_an_error(self):
        assert len(errors_of("y = x\nx = 1\n")) == 1

    def test_undefined_inside_function_is_reported(self):
        assert len(errors_of("def f():\n    return nope\n")) == 1

    def test_assignment_value_checked_before_target_bound(self):
        assert len(errors_of("x = x + 1\n")) == 1

    def test_augassign_requires_defined_target(self):
        assert len(errors_of("x += 1\n")) == 1
        assert errors_of("x = 0\nx += 1\n") == []

    @pytest.mark.parametrize(
        "source",
        [
            "for i in range(3):\n    print(i)\n",
            "with open('f') as fh:\n    fh.read()\n",
            "try:\n    pass\nexcept ValueError as e:\n    print(e)\n",
            "r = [i * 2 for i in range(3) if i]\n",
            "d = {k: v for k, v in {}.items()}\n",
            "g = (i for i in [1])\n",
            "f = lambda a, b=2: a + b\n",
            "if (n := 3) > 2:\n    print(n)\n",
            "import os.path\nprint(os.path)\n",
            "a, (b, *c) = 1, (2, 3)\nprint(a, b, c)\n",
            "class A:\n    x = 1\n    def m(self):\n        return self.x\n",
            "def f():\n    global G\n    G = 1\nf()\nprint(G)\n",
            "match 1:\n    case [x, *rest]:\n        print(x, rest)\n    case {'k': v, **others}:\n        print(v, others)\n    case int() as n:\n        print(n)\n",
            "print(__name__, __file__)\n",
            "x: int = 3\nprint(x)\n",
            "def f(a: 'Unknown') -> 'Other':\n    pass\n",
        ],
    )
    def test_common_constructs_are_not_false_positives(self, source):
        assert errors_of(source) == []

    def test_walrus_in_comprehension_binds_in_enclosing_scope(self):
        assert errors_of("[y := 1 for _ in range(3)]\nprint(y)\n") == []

    def test_comprehension_variable_does_not_leak(self):
        assert len(errors_of("r = [i for i in range(3)]\nprint(i)\n")) == 1

    def test_comprehension_target_visible_in_element(self):
        assert errors_of("r = [a + b for a in [1] for b in [2]]\n") == []

    def test_decorator_and_default_are_checked_in_enclosing_scope(self):
        assert len(errors_of("@nodeco\ndef f(a=nodefault):\n    pass\n")) == 2

    def test_from_import_star_binds_nothing(self):
        assert len(errors_of("from os import *\nprint(sep)\n")) == 1

    def test_deleting_does_not_require_name_check(self):
        assert errors_of("x = 1\ndel x\n") == []


class TestTypes:
    def test_calls_checked_with_var_imported(self):
        errs = errors_of("""
            from typeon import var
            def f(r=var(int, 6), s=var(float, 8.0)):
                pass
            f("gg", "88")
            f(1, 2.0)
            f(1, s="x")
            """)
        msgs = "\n".join(errs)
        assert len(errs) == 3
        assert "argument '0'" in msgs and "argument '1'" in msgs and "argument 's'" in msgs
        assert "'str' instead of 'int'" in msgs

    def test_call_before_definition_inside_function_is_still_checked(self):
        errs = errors_of("""
            from typeon import var
            def caller():
                f("x")
            def f(r=var(int, 6)):
                pass
            """)
        assert len(errs) == 1

    def test_numeric_tower_accepted_for_arguments(self):
        header = "from typeon import var\ndef f(a=var(int, 1), b=var(float, 1.0)):\n    return a\n"
        assert errors_of(header + "f(True, 1)\n") == []
        assert len(errors_of(header + "f(1.5, 1)\nf('x', 1.0)\n")) == 2

    def test_untyped_and_nonliteral_arguments_are_not_judged(self):
        assert (
            errors_of("""
            from typeon import var
            def f(a, r=var(int, 6)):
                pass
            v = "str"
            f("anything", v)
            f(1, undefined_ok := 3)
            """)
            == []
        )

    def test_position_mapping_with_untyped_first_parameter(self):
        errs = errors_of("""
            from typeon import var
            def f(a, r=var(int, 6)):
                pass
            f("x", "bad")
            """)
        assert len(errs) == 1 and "argument '1'" in errs[0]

    def test_extra_call_arguments_do_not_crash(self):
        assert (
            errors_of("""
            from typeon import var
            def f(r=var(int, 6), *rest):
                pass
            f(1, 2, 3, 4)
            f(*[1, 2])
            """)
            == []
        )

    def test_nested_functions_have_qualified_signatures(self):
        errs = errors_of("""
            from typeon import var
            def f(r=var(int, 6)):
                pass
            def outer():
                def f(r=var(str, "")):
                    pass
                f("ok")
            f(1)
            """)
        assert errs == []

    def test_binop_mismatch_on_typed_parameter(self):
        errs = errors_of("""
            from typeon import var
            def f(r=var(int, 6)):
                r = r + 1
                r = r + ""
            """)
        assert len(errs) == 1 and "Type mismatch between r, type<str>" in errs[0]

    @pytest.mark.parametrize(
        "expr, ok",
        [
            ("1 + 2.5", True),
            ("'a' + 1", False),
            ("'a' * 3", True),
            ("[1] * 2", True),
            ("'a' * 'b'", False),
            ("'%s' % 5", True),
            ("5 % 'x'", False),
            ("1 + True", True),
            ("b'a' + 'a'", False),
            ("x + 1", True),  # unknown type: not judged
        ],
    )
    def test_literal_binops(self, expr, ok):
        assert (errors_of("x = 1\ny = " + expr + "\n") == []) is ok


class TestErrors:
    def test_check_raises_with_all_findings_sorted(self):
        with pytest.raises(TypeonException) as info:
            check("a = one\nb = two\n")
        exc = info.value
        assert len(exc.errors) == 2
        assert "'one'" in exc.errors[0] and "'two'" in exc.errors[1]
        assert "1. " in str(exc) and "2. " in str(exc)

    def test_syntax_error_becomes_typeon_exception(self):
        with pytest.raises(TypeonException, match="syntax error"):
            check("def f(:\n")

    def test_python2_tuple_parameters_are_rejected_as_syntax_error(self):
        with pytest.raises(TypeonException, match="syntax error"):
            check("def f((int, r)):\n    pass\n")

    def test_pathologically_nested_source_is_a_typeon_exception(self):
        with pytest.raises(TypeonException):
            check("x = " + "(" * 3000 + "1" + ")" * 3000 + "\n")

    def test_scanner_does_not_mutate_tree(self):
        import ast

        src = "def f(a):\n    return a + g(1)\n"
        scanner_ = scanner.TypeonTyper(throw=False)
        tree = scanner_.handleModuleSource(src)
        assert ast.dump(tree) == ast.dump(ast.parse(src))

    def test_non_name_call_targets_do_not_remove_nodes(self):
        import ast

        src = "import os\nx = os.path.join('a', 'b')\ny = (lambda: 1)()\n"
        tree = scanner.TypeonTyper(throw=False).handleModuleSource(src)
        assert ast.dump(tree) == ast.dump(ast.parse(src))


class TestFixtureFiles:
    def test_var_syntax_fixture(self, fixtures_dir):
        typer = scanner.TypeonTyper(throw=False)
        typer.handleModuleAtPath(str(fixtures_dir / "var_syntax.py"))
        errs = [repr(e) for e in typer._errors]
        assert len(errs) == 3
        assert sum("Bad type passed" in e for e in errs) == 3

    def test_example_reports_expected_findings(self):
        from pathlib import Path

        path = Path(__file__).parent.parent / "examples" / "sample.py"
        with pytest.raises(TypeonException) as info:
            typeon.checkFile(path)
        text = str(info.value)
        for name in ("item", "jump", "'y'", "'h'"):
            assert name in text
        assert "Type mismatch" in text and text.count("Bad type passed") == 3
