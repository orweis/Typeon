# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/); versions follow
[Semantic Versioning](https://semver.org/). The 2012 code was never versioned; it is
treated as 1.x for the purpose of this log.

## 2.0.0

### License
- The project is now licensed under the Apache License 2.0 (`LICENSE`).

This is a **breaking** release. See "Migrating from the 2012 code" in the README.

### Breaking
- Python 3.11+ only. Python 2 is no longer supported (the old code did not run on Python 3 at all).
- Now a real package. `import typeon` and `from typeon import Typeon, var` work as before;
  the top-level modules `scanner`, `typeonExceptions` and `utils` no longer exist. Use
  `typeon.scanner`, `typeon.exceptions` and `typeon.utils`.
- The Python 2 tuple-parameter syntax `def f((int, r), (float, x))` is gone (it is a
  syntax error in Python 3). Use `def f(r=var(int, 6), x=var(float, 8.0))`.
- Removed `utils/osUtils.py` (`LocalTempFile`, `ResourceLocator`): unused, tied to another
  project's layout, with a path-escape and temp-file cleanup hazards.
- Scanner subclassing API changed: `TypeonScanner` is now an `ast.NodeVisitor` (was
  `ast.NodeTransformer`), so subclasses that return replacement nodes no longer rewrite the
  tree, and `handleModuleAtPath` returns the unmodified AST without type annotations. The
  hooks `visitSet`, `frameVisit`, `basicVisit`, `visit_Attribute` and
  `_handleTupleTypeMarking` were removed.
- While `compile()` re-executes a script run as `__main__`, `__name__` is
  `_typeon_fused___main__` (so `logging.getLogger(__name__)` created during the re-run has
  that name); it is restored afterwards.
- Removed unused `PyStack.listCallers/getStackDepth/listClasses`, and `scanner.AstNode`.
- Removed the scratch files `play.py` (hard-coded Windows path, removed `imp` module) and
  `test2.py` (moved to `tests/fixtures/var_syntax.py`, ported to Python 3 syntax);
  `Sample.py` moved to `examples/sample.py`.
- `dataUtils.flatten`: fixed nested sequences (previously `NameError`) and duplicated
  single-element items; keyword `flatenStrings` renamed `flattenStrings` (old name still
  accepted with a `DeprecationWarning`).

### Changed (behaviour)
- `var(int, 6)` parameters now also feed the binary-operator check (as the docs always
  implied), so `r + ""` on such a parameter is reported.
- A `bool` is accepted for `int`, and `bool`/`int` for `float` (numeric tower).
- Argument types are only judged when the argument is a literal (non-literals, such as
  variables, were previously reported as mismatches). Parameters without `var()` are
  never judged, and typed parameters are matched by position/keyword correctly.
- Names used inside function bodies are checked after the whole module has been scanned,
  so calling a function defined later is no longer reported.
- Fewer false positives: loop/with/except/comprehension/walrus/match targets, `from x import y`,
  `global`, lambdas, class scopes, `*args/**kwargs` and keyword-only parameters are handled.
- int/float/bool/complex may be mixed in binary operators; `str * int`, `list * int` and
  `str % x` are accepted.
- Scope tracking is restored after functions and classes (previously later module-level
  names were attributed to the last function).
- Signatures are keyed by qualified name, so same-named nested functions no longer collide.
- `compile()` finds the calling module from the caller's frame, not a fixed stack depth;
  the module is re-executed in its own namespace (functions share the module's globals,
  `__name__` guards do not fire during re-execution) and a `compile()` call by the module being
  re-executed is ignored (other modules imported meanwhile are still checked). Syntax errors and over-deep source raise `TypeonException`.
- The scanner no longer rewrites the AST (it returns it unchanged).

### Added
- `typeon.checkSource()` / `typeon.checkFile()`: check without executing anything.
- `TypeonException.errors`: the individual findings.
- `pyproject.toml` (version 2.0.0, zero runtime dependencies), pytest suite, ruff, GitHub
  Actions CI, README, `docs/`.

### Security
- Documented the trust model: `typeon.compile()` executes the calling module's code again.
  Only use it on code you trust; use `checkFile()` for untrusted code.
