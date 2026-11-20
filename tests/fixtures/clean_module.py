"""A module that must pass the check and be importable."""

import typeon
from typeon import var

COUNTER = []


def scale(value=var(int, 1), factor=var(float, 2.0)):
    COUNTER.append(value)
    return value * factor


def run():
    return scale(2, 3.0)


class Box:
    def __init__(self, item):
        self.item = item


typeon.compile()
