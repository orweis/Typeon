"""
 Os utilities
"""

import os
import glob
import tempfile

class LocalTempFile(object):
    """
    A temp file that can be accesed by other processes
    """

    def __init__(self, mode="w+b"):
        self.tempDir = tempfile.mkdtemp(suffix='inti')
        self.name = os.path.join(self.tempDir, "tmp_cmd_intigua")
        self.file = open(self.name, mode)
        self._guard = True

    def __enter__(self):
        return self

    def releaseGuard(self):
        self._guard = False    

    def delete(self):
        self.file.close()
        if os.path.exists(self.name):           
            os.unlink(self.name)
            os.rmdir(self.tempDir)

    def __del__(self):
        if self._guard:
            self.delete()
            
    def __exit__(self, exc_type, exc_value, traceback):
        if self._guard:
            self.delete()



class ResourceLocator(object):

    def __init__(self, currentLocation =__file__, repositoryName = "infra"):
        """
        @param repositoryName first folder under the repository root, we are nested at.
               repository will be deemd as one folder above this one.
        """
        if currentLocation.find(os.path.sep)<0:
            currentLocation = os.getcwd()
        currentLocation = os.path.abspath(currentLocation)
        pathSplit = currentLocation.split(os.path.sep)
        self._repositoryPath = os.path.sep.join(pathSplit[ : pathSplit.index(repositoryName) ])

    def globPathsInRepository(self, globPattern):

        search = os.path.join(self._repositoryPath, globPattern )
        searchWithInBetween = os.path.join(self._repositoryPath, "*", globPattern )
        return glob.glob( search ) + glob.glob( searchWithInBetween )

    def findFileInRepository(self, resourcePath):
        """
        @resource file to search for 
        @return a full path found for the sought path, saerching the repository folder
                or "" if not found.
        """
        soughtDir = os.path.dirname( resourcePath )
        soughtName = os.path.basename( resourcePath )
        justFile = soughtDir == ""
        for dir, subDirs, files in os.walk( self._repositoryPath ):
            if justFile:
                if soughtName in files:
                    return os.path.join( dir, soughtName)
            else:
                if soughtDir in dir and soughtName in files:
                    return os.path.join( dir, soughtName)
        return ""
                


