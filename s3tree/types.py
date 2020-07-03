#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Custom types."""


class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton("SingletonMeta", (object,), {})):
    pass


class S3TreeConfig(Singleton):
    def __init__(self):
        self.aws_access_key_id = None
        self.aws_secret_access_key = None
