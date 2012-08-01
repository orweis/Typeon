"""
dataUtils
"""
import collections

def flatten(collection, flatenStrings=False):
    """
    generator
    @return elements from the collection and sub collections in it
    """
    for item in collection:       
        if isinstance( item, collections.Sequence):
            if len(item) == 1:
                yield item[0]
            if (flatenStrings and isinstance(item, str)) or not isinstance(item,str):
                itemIter = flaten( item )
                for subItem in itemIter:
                    yield subItem
            else:
                yield item
        else:
            yield item


class GenericProxy(object):
    """
    A generic object proxy, that enables wrapping an object and allowing seamless access to it via the wrapper.
    
    example:
        
        class SampleA(object):
            def __init__(self):
                self.a = 1
                self.b = 2


        class SampleARepr(GenericProxy):
            def __init__(self, target):
                self._proxyWrap(target)

            def __repr__(self):
                return "a==%s b==%s" %(self.a,self.b)
        
        r=SampleARepr( SampleA() )
        >>> r.a
        1
        >>> r.b
        2
        >>> r
        a==1 b==2
    """

    _PROXY_ENABLED_INDICATOR = "_proxyEnabled"
    _PROXY_OWN_PROPS = "_ownProperties"


    def getWrappedObject(self):
        return self._proxyTarget

    def _proxyWrap(self, target, markProxyProperties = True):
        self._proxyTarget = target   
        self._ownProperties = dir(self)
        if markProxyProperties:
            buitlin = dir(object) + ["__dict__","__weakref__"]
            for item in dir(target):
                if item not in buitlin:
                    setattr( self, item, None )
        setattr(self, GenericProxy._PROXY_ENABLED_INDICATOR, True)

    def __getattribute__(self,name):

        try:
            #Check if we have a target warpped by the proxy (i.e. wrap was called)
            object.__getattribute__(self,GenericProxy._PROXY_ENABLED_INDICATOR)
        except Exception, err:
            return object.__getattribute__(self,name)            
        #If we are proxied check if this is a proxied entry or one of the properties of the wrapper
        if name not in object.__getattribute__(self,GenericProxy._PROXY_OWN_PROPS):
            return getattr(self._proxyTarget, name)
        else:
            return object.__getattribute__(self,name)     




    
