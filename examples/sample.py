"""Deliberately broken example: run it to see Typeon's error report.

    python examples/sample.py

Expected findings: undefined names (item, jump, y, h), a str + int operand
mismatch, and bad argument types in the two doMath() calls.
"""

import typeon
from typeon import var


def doMath(r=var(int, 6), fraction=var(float, 8.0), z="KKK"):
    if item is True:
        q = jump(y) + h
    r = r + 1
    r = r + ""
    return r / int(fraction)


def mainTest():
    doMath("gg", "88")
    doMath(1, "h")


typeon.compile()
