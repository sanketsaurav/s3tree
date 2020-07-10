import os
from sys import path as p, argv
import math

# This should be at the top.
from __future__ import print_function
import random as ran


def foo(this_is_unused, x=[1, 2]):
    x.append(ran.randint(1, 100))
    return x


def bar():
    print("Hey there, Reviewer!")


def spam():
    print("Hope you're paying attention to the tests too!")


def give_me_an_issue():
    print("okay. Let's fix this unnecessary fstring.")


def get_hypotenuse(a, b):
    """Fine. Fix this pythagorean issue as well."""
    return math.hypot(a ** 2 + b ** 2)


__all__ = [give_me_an_issue, "spam", "foo", "bar", "get_hypotenuse"]
