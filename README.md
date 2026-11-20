# Typeon

Typeon: Python with types. Seamlessly bring compiler-style checks and type safety to Python
and remain Pythonic. It is a small, dependency-free prototype that scans a module's AST and
reports undefined names and simple type errors.

- Concept: Or Weis (2009). Author: Or Weis (July 2012).
- Status: alpha / experimental. Version 2.0.0 (Python 3 port; see the migration notes below).
- Requires Python 3.11 or newer. No runtime dependencies.

## Install

```sh
pip install .            # from a checkout
pip install -e ".[dev]"  # for development (pytest, pytest-cov, ruff)
```

## Usage

Mark parameter types with `var(type, default)` (at runtime `var` just returns the default)
and call `typeon.compile()` at the end of the module:

```python
import typeon
from typeon import var

def scale(value=var(int, 1), factor=var(float, 2.0)):
    return value * factor

def main():
    scale("two", 3.0)      # error: 'str' instead of 'int'
    return missing_name    # error: Name 'missing_name' is not defined

typeon.compile()
```

Importing (or running) this module raises `typeon.TypeonException` with a numbered report:

```
Module "demo.py"
	1. Bad type passed to function 'scale' for argument '0'.
	    'str' instead of 'int' - (line:8 col:4 )

	2. Name 'missing_name' is not defined -(line:9 col:11 )
```

`from typeon import Typeon; Typeon.compile()` is the same call and still works.

To check a file **without executing it**:

```python
import typeon
typeon.checkFile("path/to/module.py")     # raises TypeonException on findings
typeon.checkSource("x = undefined\n")     # same, for a string/bytes
```

A deliberately broken example is in `examples/sample.py` (`python examples/sample.py`).

### What is checked

- Names used but never defined (scope aware).
- Literal arguments passed to functions whose parameters are declared with `var(...)`,
  by position and by keyword.
- Binary operators whose operands have clearly different types (literals and `var()` parameters).

See `docs/design.md` for the full status table and limitations.

## Trust model (read this)

`typeon.compile()` **executes the calling module's top-level code a second time** (in the
module's own namespace, with `__name__` guards not firing) after checking it. Module-level
side effects therefore happen twice, and a nested `compile()` during the re-run is ignored.
Only use it on code you would import anyway. For untrusted code use `checkFile` /
`checkSource`, which only parse. Source nested pathologically deeply is rejected with a
`TypeonException`, not a crash.

## Migrating from the 2012 (Python 2) code - breaking changes in 2.0.0

- Python 3.11+ only; Python 2 is not supported.
- Install as a package. `import typeon` / `from typeon import Typeon, var` are unchanged, but
  `import scanner`, `import typeonExceptions` and `from utils import ...` became
  `typeon.scanner`, `typeon.exceptions` and `typeon.utils`.
- Tuple parameters `def f((int, r))` are invalid Python 3; use `def f(r=var(int, 0))`.
- `utils.osUtils` was removed. Several checks changed (fewer false positives, `var()`
  parameters now feed operator checks). Full list in [CHANGELOG.md](CHANGELOG.md).

## Development

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest --cov          # tests (coverage floor 90%)
ruff check . && ruff format --check .
python -m build       # optional: needs `pip install build`
```

CI (GitHub Actions) runs lint and tests on Python 3.11 to 3.14.

## License

No license file is included yet; until the owner adds one, all rights are reserved by default.
