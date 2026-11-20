"""Scanner fixture (parsed, never executed): var() typed parameters with bad calls."""

import typeon
from typeon import var


class Z:
    def __init__(self):
        self.data = "GGG"


def doMath(r=var(int, 6), fraction=var(float, 8.0), z="KKK"):
    pass


def mainTest():
    doMath("gg", "88")
    doMath(1, "h")


typeon.compile()
