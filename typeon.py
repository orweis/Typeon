"""

[*] Func prototyping
[*] Variable type inference
  - also deduced from func prototype
  
[*] Function overloading

[*] Inheritance Limitations
[*] Pure Virtual methods

[*] Assertions
  -func Must change value of X
  -class must have member/method
  
  
"""

from utils import pyUtils
import scanner
import typeonExceptions
import os
import sys

class ModuleHandler(object):

    @staticmethod
    def  mapModulesByPaths():
        m = {}
        for moduleName, module in sys.modules.iteritems():
            path = getattr(module, "__file__", None)
            m[path] = m.get(path, []) + [(moduleName,module)]
        return m

    def __init__(self):
        self._modulesByPath = ModuleHandler.mapModulesByPaths()
        self._namespaces = {}
    
    def handleModule(self, modulePath):    
        #checker = scanner.TypeonChecker()
        checker = scanner.TypeonTyper()
        # //TODO Pass module object instead of path    
        res = checker.handleModuleAtPath( modulePath )
        return res        

    def fuseModule(self, moduleName, module , newModuleAst):
        # CompileAst to code
        c = compile(newModuleAst, moduleName, "exec")
        # Create a new namespace for this module
        self._namespaces[moduleName] = {}
        # Load into the namespace //TODO make Python 3 compatiable
        exec c in self._namespaces[moduleName]
        self._namespaces[moduleName].pop('__builtins__')
        #print self._namespaces[moduleName]
        # Scan resulting namesapce population and fuse
        for key,value in self._namespaces[moduleName].iteritems():
            module.__dict__[key] = value
        
        
    def handleCaller(self):
        pyStack = pyUtils.PyStack()
        modulePath = caller = pyStack.listModules()[-4]
        #print caller, pyStack.listModules()
        if os.path.isfile(caller) and __file__ != caller:
            newModuleAst = self.handleModule(caller)
            modules = self._modulesByPath.get(modulePath, None)
            if modules is None:
                modules = self._modulesByPath.get(modulePath + "c", None)
            if modules is None:
                raise ImportError("Module path %s not found" %modulePath)
            if len(modules) != 1:
                raise ImportError("Couldn't detect single module name for path %s" %modulePath)
            moduleName, module = modules[0]
        else:
            raise ImportError("Module %s wasn't given as a full path" %modulePath)       
        self.fuseModule(moduleName, module , newModuleAst)

        



def compile():
    try:
        handler = ModuleHandler()
        handler.handleCaller()
    except typeonExceptions.TypeonException, typeonErr:
        raise typeonErr





##class Prototype(object):
##
##    def __init__(self, *args, **kwargs):
##        self.__args   = args
##        self.__kwargs = kwargs
##        
##    def __call__(self, target):
##        print target
##        return target
##        
##        
##        
##        
##
##prototype = Prototype
##
##
##class Foo:
##    pass
##    
##
##
##@prototype(int, str, Foo)
##def func(a,b,c) :
##    x = a
##    x
##

