"""AST scanners: name checking and basic type checking for Python source.

Class hierarchy::

    TypeonScanner      walks the AST, tracks scopes (``StackFrame``) and bound names
      TypeonChecker    + reports names that are used but never defined
        TypeonTyper    + checks call argument types and binary operator operands
                         for parameters typed with ``var(type, default)``

The scanners never modify the tree and never execute the code they scan.
"""

import ast
import builtins

from . import exceptions as typeonExcept


class Consts:
    DEF_TYPE = "var"


# Names that are always available to module level code.
_MODULE_NAMES = frozenset(
    [
        "__name__",
        "__file__",
        "__doc__",
        "__package__",
        "__spec__",
        "__loader__",
        "__path__",
        "__cached__",
        "__annotations__",
        "__builtins__",
        "__class__",
        "__module__",
        "__qualname__",
    ]
)

_NUMERIC = frozenset(["int", "float", "bool", "complex"])
_SEQUENCES = frozenset(["str", "bytes", "list", "tuple"])


class AstUtils:
    @staticmethod
    def attributeToSingleName(attribute):
        """Translate an attribute chain to a single string: ``a.b.c`` -> ``"a.b.c"``."""
        res = ""
        if isinstance(attribute.value, ast.Attribute):
            res += AstUtils.attributeToSingleName(attribute.value)
        elif isinstance(attribute.value, ast.Name):
            res = attribute.value.id
        res += "." + attribute.attr
        return res

    @staticmethod
    def nodeToName(node):
        """Return a printable name for ``node`` or ``None`` if it has none."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return AstUtils.attributeToSingleName(node)
        if isinstance(node, ast.arg):
            return node.arg
        if isinstance(node, ast.alias):
            # ``import a.b`` binds ``a``; ``import a.b as c`` binds ``c``.
            return node.asname or node.name.split(".")[0]
        name = getattr(node, "name", None)
        if isinstance(name, str):
            return name
        nodeType = AstUtils.nodeToType(node)
        if nodeType is not None:
            return "type<%s>" % nodeType
        return None

    _CONTAINER_TYPES = {
        ast.Tuple: "tuple",
        ast.List: "list",
        ast.Dict: "dict",
        ast.Set: "set",
    }

    # bool must precede int: bool is a subclass of int.
    _CONSTANT_TYPES = (
        (bool, "bool"),
        (int, "int"),
        (float, "float"),
        (complex, "complex"),
        (str, "str"),
        (bytes, "bytes"),
    )

    @staticmethod
    def nodeToType(node):
        """Return the Python type name of a literal node, or ``None`` if unknown."""
        if isinstance(node, ast.Constant):
            for pyType, name in AstUtils._CONSTANT_TYPES:
                if isinstance(node.value, pyType):
                    return name
            return None
        return AstUtils._CONTAINER_TYPES.get(type(node))


class StackFrame:
    """A lexical scope: the names bound in it, its sub scopes and variable types."""

    def __init__(self, name="", level=0, parentFrame=None, deferred=False):
        self._level = level
        self._name = name
        self._objectMap = {}
        self._types = {}
        self._parentFrame = parentFrame
        self._subFrames = []
        # Names used in a deferred scope are checked at the end of the scan,
        # because function bodies run after the whole module has been defined.
        self.deferred = deferred

    def addFrame(self, name, deferred=False):
        newFrame = StackFrame(
            name=name,
            level=self._level + 1,
            parentFrame=self,
            deferred=deferred or self.deferred,
        )
        self._subFrames.append(newFrame)
        return newFrame

    @property
    def parent(self):
        return self._parentFrame

    def getName(self):
        """Dotted qualified name of the scope, e.g. ``Outer.method``; ``""`` for the module."""
        parts = []
        frame = self
        while frame is not None and frame._name:
            parts.append(frame._name)
            frame = frame._parentFrame
        return ".".join(reversed(parts))

    def addName(self, name, obj=None):
        if name is not None:
            self._objectMap[name] = obj

    def addObject(self, obj):
        self.addName(AstUtils.nodeToName(obj), obj)

    def hasName(self, name):
        frame = self
        while frame is not None:
            if name in frame._objectMap:
                return True
            frame = frame._parentFrame
        return False

    def getAvailableObjectNames(self):
        names = list(self._objectMap)
        if self._parentFrame is not None:
            names = self._parentFrame.getAvailableObjectNames() + names
        return names

    def setType(self, name, typeName):
        self._types[name] = typeName

    def getType(self, name):
        frame = self
        while frame is not None:
            if name in frame._objectMap:
                return frame._types.get(name)
            frame = frame._parentFrame
        return None

    def __repr__(self):
        out = str(list(self._objectMap))
        if self._subFrames:
            out += " - "
            for frame in self._subFrames:
                out += "\n%s%s" % ("\t" * self._level, frame)
        return out


class TypeonScanner(ast.NodeVisitor):
    """Walks a module AST, maintaining scopes. Subclasses add checks via hooks."""

    def __init__(self):
        self._handling = ""
        self._stack = StackFrame()
        self._currentFrame = self._stack
        self._builtInNames = frozenset(dir(builtins))
        self._typeNames = self._builtInNames
        for name in _MODULE_NAMES:
            self._stack.addName(name)
        self._finalizers = []

    # -- public API -----------------------------------------------------

    def handleModuleAtPath(self, modulePath):
        with open(modulePath, "rb") as inData:
            data = inData.read()
        return self.handleModuleSource(data, modulePath)

    def handleModuleSource(self, source, filename="<string>"):
        """Parse and scan ``source`` (``str`` or ``bytes``)."""
        self._handling = filename
        try:
            moduleAsAst = ast.parse(source, filename=filename)
        except SyntaxError as err:
            raise typeonExcept.TypeonException(
                'Module "%s": syntax error: %s (line %s)' % (filename, err.msg, err.lineno)
            ) from err
        except (RecursionError, MemoryError, ValueError) as err:
            raise typeonExcept.TypeonException(
                'Module "%s" could not be parsed: %s' % (filename, type(err).__name__)
            ) from err
        return self.handleModuleAst(moduleAsAst)

    def handleModuleAst(self, moduleAsAst):
        return self.scan(moduleAsAst)

    def scan(self, astNode):
        """Perform a Typeon scan on the given AST root node and return it unchanged."""
        try:
            self.visit(astNode)
            for finalizer in self._finalizers:
                finalizer()
        except RecursionError as err:
            raise typeonExcept.TypeonException(
                'Module "%s" is nested too deeply to be scanned' % self._handling
            ) from err
        return astNode

    @property
    def stack(self):
        return self._stack

    @property
    def currentStackFrame(self):
        return self._currentFrame

    @property
    def currentModule(self):
        """The path of the module currently being handled."""
        return self._handling

    # -- scope helpers ---------------------------------------------------

    def _pushFrame(self, name, deferred=False):
        self._currentFrame = self._currentFrame.addFrame(name, deferred)
        return self._currentFrame

    def _popFrame(self):
        self._currentFrame = self._currentFrame.parent

    def _bind(self, name):
        self._currentFrame.addName(name)

    def addObject(self, node):
        """Bind the name(s) carried by ``node`` in the current scope."""
        if isinstance(node, (ast.Tuple, ast.List)):
            for member in node.elts:
                self.addObject(member)
        elif isinstance(node, ast.Starred):
            self.addObject(node.value)
        else:
            self._currentFrame.addObject(node)
        return node

    def _bindTypeParams(self, node):
        for param in getattr(node, "type_params", None) or []:
            self._bind(param.name)

    # -- hooks -----------------------------------------------------------

    def onLoadName(self, node):
        """Called for every name that is read."""

    def addArg(self, node, defValue=None, position=None):
        """Bind a function parameter (``node`` is an ``ast.arg``)."""
        self._bind(node.arg)
        return node

    # -- visitors --------------------------------------------------------

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.onLoadName(node)
        elif isinstance(node.ctx, ast.Store):
            self._bind(node.id)

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
        self.visit(node.target)

    def visit_AugAssign(self, node):
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self.onLoadName(node.target)
        else:
            self.visit(node.target)

    def visit_NamedExpr(self, node):
        self.visit(node.value)
        self.visit(node.target)

    def visit_Import(self, node):
        for alias in node.names:
            self._bind(AstUtils.nodeToName(alias))

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name != "*":
                self._bind(AstUtils.nodeToName(alias))

    def visit_Global(self, node):
        for name in node.names:
            self._stack.addName(name)

    def visit_ExceptHandler(self, node):
        if node.type is not None:
            self.visit(node.type)
        self._bind(node.name)
        for stmt in node.body:
            self.visit(stmt)

    def visit_MatchAs(self, node):
        self._bind(node.name)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        self._bind(node.rest)
        self.generic_visit(node)

    def visit_TypeAlias(self, node):
        self.addObject(node.name)
        self._bindTypeParams(node)

    def _visitComprehension(self, node, elements):
        self._pushFrame("<comprehension>")
        for generator in node.generators:
            self.visit(generator.iter)
            self.visit(generator.target)
            for cond in generator.ifs:
                self.visit(cond)
        for element in elements:
            self.visit(element)
        self._popFrame()

    def visit_ListComp(self, node):
        self._visitComprehension(node, [node.elt])

    visit_SetComp = visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node):
        self._visitComprehension(node, [node.key, node.value])

    def visit_Lambda(self, node):
        for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
            self.visit(default)
        self._pushFrame("<lambda>", deferred=True)
        for arg in self._allArgs(node.args):
            self._bind(arg.arg)
        self.visit(node.body)
        self._popFrame()

    @staticmethod
    def _allArgs(args):
        result = list(args.posonlyargs) + list(args.args)
        if args.vararg:
            result.append(args.vararg)
        result += args.kwonlyargs
        if args.kwarg:
            result.append(args.kwarg)
        return result

    def visit_FunctionDef(self, node):
        # Decorators and defaults are evaluated in the enclosing scope.
        for decorator in node.decorator_list:
            self.visit(decorator)
        args = node.args
        for default in args.defaults + [d for d in args.kw_defaults if d is not None]:
            self.visit(default)
        self._bindTypeParams(node)
        self.addObject(node)
        self._pushFrame(node.name, deferred=True)
        self._handleArguments(args)
        for stmt in node.body:
            self.visit(stmt)
        self._popFrame()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _handleArguments(self, args):
        positional = list(args.posonlyargs) + list(args.args)
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        for position, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
            self.addArg(arg, default, position)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            self.addArg(arg, default, None)
        for arg in (args.vararg, args.kwarg):
            if arg is not None:
                self.addArg(arg, None, None)

    def visit_ClassDef(self, node):
        for expr in node.decorator_list + node.bases + [k.value for k in node.keywords]:
            self.visit(expr)
        self._bindTypeParams(node)
        self.addObject(node)
        self._pushFrame(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self._popFrame()


class TypeonErrorMark:
    """Base class for marking detected errors."""

    def __init__(self, astNode):
        self._node = astNode

    @property
    def position(self):
        return (getattr(self._node, "lineno", 0), getattr(self._node, "col_offset", 0))

    def _pos(self):
        return "(line:%s col:%s )" % self.position


class NameErrorMark(TypeonErrorMark):
    def __repr__(self):
        return "Name '%s' is not defined -%s" % (self._node.id, self._pos())


class TypeonChecker(TypeonScanner):
    """Reports names that are used but not defined."""

    def __init__(self, throw=True):
        super().__init__()
        self._throw = throw
        self._errors = []
        self._finalizers.append(self._checkDeferredNames)
        self._deferredNames = []

    @property
    def errors(self):
        return list(self._errors)

    def _isDefined(self, frame, name):
        return frame.hasName(name) or name in self._builtInNames

    def onLoadName(self, node):
        frame = self.currentStackFrame
        if frame.deferred:
            self._deferredNames.append((frame, node))
        elif not self._isDefined(frame, node.id):
            self._errors.append(NameErrorMark(node))

    def _checkDeferredNames(self):
        for frame, node in self._deferredNames:
            if not self._isDefined(frame, node.id):
                self._errors.append(NameErrorMark(node))

    def scan(self, astNode):
        result = super().scan(astNode)
        if self._errors and self._throw:
            self._errors.sort(key=lambda mark: mark.position)
            messages = [repr(err) for err in self._errors]
            report = 'Module "%s" \n' % self.currentModule
            for index, message in enumerate(messages, 1):
                report += "\t%d. %s\n\n" % (index, message)
            raise typeonExcept.TypeonException(report, errors=messages)
        return result


class CallSignature:
    """Declared parameter types of a function, by position and by name."""

    def __init__(self):
        self._positional = {}
        self._named = {}

    def addArg(self, type, name=None, position=None):
        if name is not None:
            self._named[name] = type
        if position is not None:
            self._positional[position] = type

    def getArg(self, id):
        """Return the declared type for a position (int) or name; ``None`` if untyped."""
        if isinstance(id, int):
            return self._positional.get(id)
        return self._named.get(id)


class TypeErrorMark(TypeonErrorMark):
    pass


class CallTypeErrorMark(TypeErrorMark):
    def __init__(self, astNode, func, argIndex, arg, passedType, expectedType):
        TypeErrorMark.__init__(self, astNode)
        self._func = func
        self._arg = arg
        self._argIndex = argIndex
        self._type = passedType
        self._expectedType = expectedType

    def __repr__(self):
        return (
            "Bad type passed to function '%s' for argument '%s'."
            "\n\t    '%s' instead of '%s' - %s"
            % (self._func, self._argIndex, self._type, self._expectedType, self._pos())
        )


class OpTypeErrorMark(TypeErrorMark):
    def __init__(self, astNode, operator, operands=None):
        TypeErrorMark.__init__(self, astNode)
        self._operator = operator
        self._operands = list(operands or [])

    def __repr__(self):
        names = [AstUtils.nodeToName(operand) for operand in self._operands]
        operands = ", ".join(name for name in names if name is not None)
        return "Type mismatch between %s using operator '%s'. - %s" % (
            operands,
            self._operator.__class__.__name__,
            self._pos(),
        )


class TypeonTyper(TypeonChecker):
    """Adds type checks for parameters declared as ``name=var(type, default)``."""

    def __init__(self, throw=True):
        super().__init__(throw)
        self._signatures = {}  # qualified function name -> CallSignature
        self._calls = []  # (frame, call node), resolved after the scan
        self._finalizers.append(self._checkCalls)

    def addArg(self, node, defValue=None, position=None):
        super().addArg(node, defValue, position)
        typeName = self._declaredType(defValue)
        if typeName is not None:
            name = node.arg
            self.currentStackFrame.setType(name, typeName)
            funcName = self.currentStackFrame.getName()
            sig = self._signatures.setdefault(funcName, CallSignature())
            sig.addArg(typeName, name, position)
        return node

    def _declaredType(self, defValue):
        """Return the type name from a ``var(type, default)`` default, else ``None``."""
        if (
            isinstance(defValue, ast.Call)
            and isinstance(defValue.func, ast.Name)
            and defValue.func.id == Consts.DEF_TYPE
            and len(defValue.args) == 2
        ):
            typeNode = defValue.args[0]
            if isinstance(typeNode, ast.Name) and typeNode.id in self._typeNames:
                return typeNode.id
        return None

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self._calls.append((self.currentStackFrame, node))
        # //TODO support methods / lambdas and so on ...
        self.generic_visit(node)

    def _findSignature(self, frame, funcName):
        while frame is not None:
            qualified = frame.getName()
            sig = self._signatures.get(qualified + "." + funcName if qualified else funcName)
            if sig is not None:
                return sig
            frame = frame.parent
        return None

    def _checkCalls(self):
        for frame, node in self._calls:
            sig = self._findSignature(frame, node.func.id)
            if sig is None:
                continue
            for index, arg in enumerate(node.args):
                if isinstance(arg, ast.Starred):
                    break
                self._checkArg(node, sig, index, arg)
            for keyword in node.keywords:
                if keyword.arg is not None:
                    self._checkArg(node, sig, keyword.arg, keyword.value)

    def _checkArg(self, node, sig, id, arg):
        expected = sig.getArg(id)
        passed = AstUtils.nodeToType(arg)
        # Only literals have a known type; anything else is not judged.
        if expected is not None and passed is not None and passed != expected:
            self._errors.append(CallTypeErrorMark(node, node.func.id, id, arg, passed, expected))

    def _typeOf(self, node):
        nodeType = AstUtils.nodeToType(node)
        if nodeType is None and isinstance(node, ast.Name):
            nodeType = self.currentStackFrame.getType(node.id)
        return nodeType

    @staticmethod
    def _compatible(op, leftType, rightType):
        if leftType is None or rightType is None:
            return True
        if isinstance(op, ast.Mult) and (leftType in _SEQUENCES or rightType in _SEQUENCES):
            # sequence repetition: exactly one sequence and one integer
            pair = {leftType, rightType}
            return len(pair & _SEQUENCES) == 1 and bool(pair & {"int", "bool"})
        if leftType == rightType:
            return True
        if leftType in _NUMERIC and rightType in _NUMERIC:
            return True
        if isinstance(op, ast.Mod):
            return leftType in ("str", "bytes")
        return False

    def checkTypeCompatibility(self, nodes, op=None):
        types = [self._typeOf(node) for node in nodes]
        return self._compatible(op, types[0], types[1])

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if not self.checkTypeCompatibility([node.left, node.right], node.op):
            self._errors.append(OpTypeErrorMark(node, node.op, [node.left, node.right]))
