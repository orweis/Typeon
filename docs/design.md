# Design notes and status

Typeon scans a module's AST and reports problems before the module's code is used.
`typeon.compile()` additionally re-executes the module (see README, "Trust model").

## What is implemented

| Feature | Status |
|---|---|
| Undefined-name detection (scope aware: functions, classes, comprehensions, lambdas, imports, match) | Implemented |
| Function "prototypes" via `param=var(type, default)`; literal call arguments checked by position and keyword | Implemented |
| Type deduced from the prototype for binary-operator checks inside the function | Implemented (parameters only) |
| Binary-operator operand mismatch for literals and typed parameters | Implemented |
| Function overloading | Not implemented. The original notes listed it; signatures are keyed by qualified name, one per name |
| Inheritance limitations, pure virtual methods | Not implemented (2012 wish list) |
| Assertions (function must change value of X; class must have member) | Not implemented (2012 wish list) |
| Attribute existence checks | Not implemented (`//TODO` in the scanner) |
| Method / lambda call checks | Not implemented |

## Layout

- `typeon/__init__.py` public API: `compile`, `Typeon.compile`, `var`, `checkSource`, `checkFile`.
- `typeon/_fuse.py` find the caller module, check it, re-execute it in place.
- `typeon/scanner.py` `TypeonScanner` (scopes), `TypeonChecker` (names), `TypeonTyper` (types).
- `typeon/utils/` small helpers (`flatten`, `GenericProxy`, `PyStack`).

## Known limitations

- Type inference is limited to `var()`-typed parameters and literals.
- Only literal arguments are type-checked at call sites.
- Class-body names are visible to methods (more permissive than Python).
- Annotations are not scanned.
