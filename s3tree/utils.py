#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility functions for S3Tree."""
from math import log
from six import string_types
from .exceptions import InvalidPathError

SUFFIXES = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']


def normalize_path(path):
    """Take a path and return the normalized path which is usable in boto3.

    We need to make sure that any path that has to be used internally:
        - must not start with a '/'
        - must end with a '/'

    Also, if there's no path, we should always default to an empty string.

    Args:
        path (string)

    Returns:
        string
    """

    if not (path is None or isinstance(path, string_types)):
        raise InvalidPathError

    if not path or path == '/':
        return ""

    # make sure the path never starts with a '/'
    path = path.lstrip('/')

    # make sure the path always ends with a '/'
    if not path.endswith('/'):
        path += '/'

    return path


def humanize_file_size(size):
    """Convert the size of a file given in bytes to a human friendly
    display value.

    >>> humanize_file_size(1700)
    '1.66 KB'

    >>> humanize_file_size(133)
    '133 bytes'

    """
    # determine binary order in steps of size 10
    # (coerce to int, // still returns a float)
    order = int(log(size, 2) / 10) if size else 0
    # format file size
    # (.4g results in rounded numbers for exact matches and max 3 decimals,
    # should never resort to exponent values)
    return '{:.4g} {}'.format(
        float(size) / (1 << (order * 10)), SUFFIXES[order]
    )


class cached_property(object):
    """
    Descriptor (non-data) for building an attribute on-demand on first use.
    """
    def __init__(self, factory):
        """
        <factory> is called such: factory(instance) to build the attribute.
        """
        self._attr_name = factory.__name__
        self._factory = factory

    def __get__(self, instance, owner):
        # Build the attribute.
        attr = self._factory(instance)

        # Cache the value; hide ourselves.
        setattr(instance, self._attr_name, attr)

        return attr
