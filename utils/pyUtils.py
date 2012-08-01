"""
Python utilities
"""
import inspect
import traceback

class PyStack(object):
    """
    A Helper class to retrive info about the Python Stack
    """

    def __init__(self):
        self.__callerFrame = inspect.currentframe().f_back
        self._stack = traceback.extract_stack()
        self._callers = [frame[2]for frame in self._stack]
        
    def listFrames(self):
        frame = self.__callerFrame
        frames = []
        while frame is not None:
            frames.append(frame)
            frame = frame.f_back
        return frames

    def listModules(self):
        return [frame[0]for frame in self._stack]

    def listCallers(self):
        return self._callers    

    def listFrameNames(self):
        return [f.f_code.co_name for f in self.listFrames() ]

    def listClasses(self):
        """
        @return a list of classes - a class for each frame which is a method, and None otherwise (functions which are not methods)
        @note special cases were added to support intigua Policy enchanced funtions. (i.e. checking globals for self)
        """
        classes = []
        for f in self.listFrames():
            firstVarName = ( f.f_code.co_varnames +(None,))[0]
            options = [f.f_locals.get(firstVarName, None),
                       f.f_locals.get('self', None),
                       f.f_globals.get('self', None)]
            instance = None
            for option in options:
                if option is not None and hasattr(option, '__class__' ):
                    instance = option
                    break
            classes.append( instance )
        return classes
            
    def getStackDepth(self,start=2,end=-1):
        """
        """
        return len(self._callers[start:end])
        
        
    def __repr__(self):
        return "".join(["%s->" %(item) for item in self._callers[2:-1] ])                
        
