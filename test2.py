from typeon import Typeon, var


class Z:
    def __init__(self):
        self.data = "GGG"

#New style types
##def doMath( r = int(6), fraction=float() , z="KKK" ):


def doMath( r = var(int,6), fraction = var(float,8) , z="KKK" ):
    pass

##def doMath( r = int(6), fraction=float() , z="KKK" ):
##    pass
##
##
##    
##def doMath( (int,r), (float,fraction) , z="KKK" ):
##    if item is True:
##        q = (jump(y) + h)
##    r = r + 1
##    r = r + ""
##    return r / int(fraction)


def mainTest():
    doMath("gg", "88")
    doMath(1, "h")
    


Typeon.compile()