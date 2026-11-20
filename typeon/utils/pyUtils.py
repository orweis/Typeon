"""Python runtime helpers."""

import inspect
import traceback


class PyStack:
    """Snapshot of the Python call stack at construction time."""

    def __init__(self):
        self.__callerFrame = inspect.currentframe().f_back
        self._stack = traceback.extract_stack()

    def listFrames(self):
        """Frame objects, innermost caller first."""
        frame = self.__callerFrame
        frames = []
        while frame is not None:
            frames.append(frame)
            frame = frame.f_back
        return frames

    def listModules(self):
        """File names of the stack entries, outermost first."""
        return [entry.filename for entry in self._stack]

    def listFrameNames(self):
        return [f.f_code.co_name for f in self.listFrames()]

    def __repr__(self):
        return "".join("%s->" % entry.name for entry in self._stack[2:-1])
