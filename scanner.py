import ast
import copy

from utils import dataUtils
import typeonExceptions as typeonExcept



class AstNode(dataUtils.GenericProxy):
    def __init__(self, target):
        self._proxyWrap(target)
        self._type = None

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value
    
        
    def __repr__(self):
        wrapped = self.getWrappedObject()
        out = "Ast%s{ " %(wrapped.__class__.__name__)
        out += " %s " %(AstUtils.nodeToName(wrapped))
        for item in dir(wrapped):
            if item in ["id", "name", "lineno", "col_offset"]:
                out += "%s: %s, " %(item,getattr(wrapped,item))
        out = out[:-1] + " }"
        return out


    
class AstUtils(object):
    @staticmethod
    def attributeToSingleName(attribute):
        """
        Transalte an ast attribute sequance to a single string-
        a.b.c  -> "a.b.c"
        """
        res = ""
        if isinstance(attribute.value, ast.Attribute):
            res += AstUtils.attributeToSingleName(attribute.value)
        elif isinstance(attribute.value, ast.Name):
            res = attribute.value.id
        res += "." + attribute.attr
        return res
    
    @staticmethod
    def nodeToName(node):
        #Unwrapp warpper if found
        if isinstance(node,AstNode):
            node = node.getWrappedObject()

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return AstUtils.attributeToSingleName(node)
        elif getattr(node, "asname",None) is not None:
            return node.asname
        elif getattr(node, "name", None) is not None:
            #Name for Imports
            return node.name
        else:
            nodeType = AstUtils.nodeToType(node)
            if nodeType is not None:
                return "type<%s>"%(nodeType)
            else:
                return None


    nodeToTypeMap = {
        ast.Str     :   "str",
        ast.Num     :   "number",
        ast.Tuple   :   "tuple",
        ast.List    :   "list",
        ast.Dict    :   "dict"
    }
    
    @staticmethod
    def nodeToType(node):
        """
        @return the Python type name of the given node if applicable;
         or None otherwise
        """
        res = None
        res = AstUtils.nodeToTypeMap.get( node.__class__, None)
        if res == "number":
            if isinstance( node.n, int):
                return "int"
            elif isinstance(node.n, float):
                return "float"
        return res
        
    
class StackFrame(object):

    def __init__(self, name = "", level = 0, parentFrame = None):
        self._level  = level
        self._name = name
        self._objects = []
        self._objectMap = {}
        self._parentFrame = parentFrame
        self._subFrames = []

    def addFrame(self, name):
        newFrame = StackFrame(name=name,level= self._level+1, parentFrame=self)
        self._subFrames.append( newFrame )
        return newFrame

    def getName(self):
        name = ""
        if self._parentFrame is not None:
            parentName = self._parentFrame.getName()
            if parentName is not None:
                name += parentName + "."
        name += self._name
        return self._name 
    

    def addObject(self, obj):
        self._objects.append(obj)
        name = AstUtils.nodeToName(obj)
        self._objectMap[name] = obj

    def getAvailableObjectNames(self):
        available = []
        if self._parentFrame is not None:
            available += self._parentFrame.getAvailableObjectNames() + self._objectMap.keys()
        else:
            available += self._objectMap.keys()
        return available


    def __repr__(self):
        out = str(self._objectMap.keys())
        if len( self._subFrames) > 0:
            out += " - "
            for stack in self._subFrames:
                out += "\n%s%s" %("\t"*self._level,stack)
        return out
    

class TypeonScanner(ast.NodeTransformer):
    """
    """

    def __init__(self):
        self._handling = ""
        self._nodes = []
        self._stack = StackFrame()
        self._currentFrame = self._stack
        if isinstance(__builtins__,dict):
            self._builtInNames = __builtins__.keys()
        else:
            self._builtInNames = __builtins__.__dict__.keys()
        self._typeNames = self._builtInNames[:]
        

    def visit_Name(self, node):
        return self.basicVisit(node)

    def visit_Call(self, node):
        return self.basicVisit(node)   


    def visit_Attribute(self, node):
        # //TODO add checks for attribute existence
        self.addObject(node)
        return self.basicVisit(node)   

    def addObject(self, node):
        #Recurse for tuples
        if isinstance(node, ast.Tuple):
            for member in node.elts:
                self.addObject( member )
        #Set the arguments
        self._currentFrame.addObject( AstNode(node) )
        return node

    def visit_FunctionDef(self, node):
        #Record the function and dive in the stack
        self.addObject(node)
        self._currentFrame = self._currentFrame.addFrame(node.name)
        #Handle all defined arguments
        newArgs = []
        changedArgs = False
        for arg in node.args.args:
            newArg = self.addObject(arg)
            newArgs.append( newArg )
            if id(newArg) != id(arg) :
                changedArgs = True
        if changedArgs:
            newNode = copy.deepcopy(node)
            newNode.args.args = newArgs
            return self.basicVisit(newNode)
        else:
            return self.basicVisit(node)

    def visit_ClassDef(self, node):
        return self.frameVisit(node)

    def visit_Import(self, node):
        for name in node.names:
            self.addObject(name)
        return self.basicVisit(node)

    def visit_Assign(self, node):
        return self.visitSet(node)

    def visitSet(self, node):
        newTargets = []
        #Scan assigned value
        newValue = self.visit(node.value)
        #Update changes if happened
        if id(newValue) != id(node.value):
            node.value = newValue
        #Scan all targets
        for target in node.targets:
            self.addObject(target)
        return self.basicVisit(node)

    def frameVisit(self,node):
        #Record the function and dive in the stack
        self.addObject(node)
        self._currentFrame = self._currentFrame.addFrame(node.name)
        return self.basicVisit(node)

    def basicVisit(self,node):
        self._nodes.append(AstNode(node))
        if hasattr(node,"body"):
            for subNode in node.body:
                # //TODO Changes (return value) of subNodes should be propgated up
                self.visit(subNode)
        return node

    def handleModuleAtPath(self, modulePath):
        with open(modulePath, "rb") as inData:
            data = inData.read()
        self._handling = modulePath
        moduleAsAst = ast.parse(data)
        return self.handleModuleAst(moduleAsAst)

    def handleModuleAst(self, moduleAsAst):
        return self.scan(moduleAsAst)

    def scan(self, astNode):
        """
        Perform a Typeon scan on the given ast root node.
        """
        res = self.visit(astNode)
        return res
        

    @property
    def stack(self):
        return self._stack

    @property
    def currentStackFrame(self):
        return self._currentFrame
    

    @property
    def currentModule(self):
        """
        @return Current module being handled by the scanner.
        """
        return self._handling


class TypeonErrorMark(object):
    """
    Base class for marking detected erros.
    """

    def __init__(self, astNode):
        self._node = astNode

        
class NameErrorMark(TypeonErrorMark):
    def __repr__(self):
        return "Name '%(id)s' is not defined -(line:%(lineno)s col:%(col_offset)s )"%self._node.__dict__

class TypeonChecker(TypeonScanner):

    def __init__(self,throw = True ):
        TypeonScanner.__init__(self)
        self._throw = throw
        self._errors = []

    def visit_Call(self, node):
        self.visit_Name(node.func)
        for index,arg in zip(range(0,len(node.args)),node.args):
            if isinstance(arg, ast.Name):
                self.visit_Name(arg)
        return TypeonScanner.visit_Call(self,node)
        

    def scan(self, astNode):
        result = TypeonScanner.scan(self, astNode)
        if self._errors != [] and self._throw:
            report = 'Module "%s" \n' %(self.currentModule)
            index = 1
            for err in self._errors:
                report += "\t%d. %s\n\n"%(index, err)
                index += 1
            raise typeonExcept.TypeonException(report)
        return result

    def visit_Name(self, node):
        newNode = super(TypeonChecker, self).visit_Name(node)
        if hasattr(newNode, "id"):
            availableObjectNames = self.currentStackFrame.getAvailableObjectNames() 
            if newNode.id not in availableObjectNames and newNode.id not in self._builtInNames:
                self._errors.append(NameErrorMark(newNode))
        return newNode





class CallSignature(object):

    def __init__(self):
        self._args = []
        self._kwargs = {}

    def addArg(self, type, name=None ):
        if name is not None:
            self._kwargs[name] = type
        self._args.append(type)

    def getArg(self, id):
        """
        @param id index or name
        """
        if isinstance(id,int):
            return self._args[id]
        else:
            return self._kwargs[id]
    


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
        pos = "(line:%(lineno)s col:%(col_offset)s )"%self._node.__dict__
        return "Bad type passed to function '%s' for argument '%s'." \
               "\n\t    '%s' instead of '%s' - %s" %(self._func, self._argIndex, self._type, self._expectedType ,pos)


class OpTypeErrorMark(TypeErrorMark):
    def __init__(self, astNode, operator, operands = []):
        TypeErrorMark.__init__(self, astNode)
        self._operator = operator
        self._operands = operands

        
    def __repr__(self):
        pos = "(line:%(lineno)s col:%(col_offset)s )"%self._node.__dict__
        operands = ", ".join([item for item in [AstUtils.nodeToName(operand) for operand in self._operands] if item is not None])
        return "Type mismatch between %s using opertaor '%s'. - %s" %(operands, self._operator.__class__.__name__ ,pos)
    


class TypeonTyper(TypeonChecker):


    def __init__(self, throw = True):
        TypeonChecker.__init__(self, throw)
        self._types = {} # {varibaleName : type}
        self._signatures = {} # FuncNameFullName: {argName : type}

    def visit_Call(self, node):
        if isinstance(node.func,ast.Name):
            sig = self._signatures.get(node.func.id,None)
            if sig is not None:
                for index,arg in zip(range(0,len(node.args)),node.args):
                    sigType = sig.getArg(index)
                    argType = AstUtils.nodeToType(arg)
                    if argType != sigType:
                        self._errors.append(CallTypeErrorMark(node, node.func.id, index, arg, argType, sigType))            
            return TypeonChecker.visit_Call(self, node)
        else:
            pass
            # //TODO support methods / lambdas and so on ...
            # print AstNode(node.func)



    def checkTypeCompatibility(self, nodes):
        nodeTypes = []
        for node in nodes:
            nodeType = AstUtils.nodeToType(node)
            #Check type is a basic type value node
            if nodeType is not None:
               nodeTypes.append(nodeType)
            #Check type of a variable
            else: 
                nodeType = self._types.get(AstUtils.nodeToName(node), None)
                if nodeType is not None:
                    nodeTypes.append(nodeType)
        for nodeType in nodeTypes:
            for otherNodeType in nodeTypes:
                if otherNodeType != nodeType:
                    return False
        return True
            
                
        


    #BinOp(expr left, operator op, expr right)
    def visit_BinOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        if not self.checkTypeCompatibility( [node.left, node.right]):
            self._errors.append(OpTypeErrorMark(node, node.op, [node.left, node.right] ))
        return self.basicVisit(node)
            

    def addObject(self, node):
        foundType = None
        #Recurse for tuples
        if isinstance(node, ast.Tuple):
            names = node.elts
            if len(node.elts) >= 2:
               typeMark = node.elts[0]
               #If we actaully received a type this means this is a Typeon defintion
               if isinstance(typeMark, ast.Name) and typeMark.id in self._typeNames:
                   #Save the type aside and keep the names attached to it
                   foundType = typeMark.id
                   names = names[1:]
            newNames = []
            for member in names:
                newMember = self.addObject( member )
                newNames.append( newMember )
                if foundType is not None:
                    newMember.type = foundType
                    self._types[AstUtils.nodeToName(member)] = foundType
                    sig = self._signatures.get(self.currentStackFrame.getName(), CallSignature() )
                    sig.addArg(foundType, AstUtils.nodeToName(member))
                    self._signatures[self.currentStackFrame.getName()] = sig

            if foundType is not None:
                newNode = copy.deepcopy(node)
                if len(newNames) == 1:
                    newNode = newNames[0]
                else:
                    newNode.elts = newNames
                self.currentStackFrame.addObject( AstNode(newNode) )
                return newNode
                    
        self.currentStackFrame.addObject( AstNode(node) )
        return node
    
    