#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Utility functions for S3Tree."""

from .exceptions import InvalidPathError


def normalize_path(path):
    """Take a path and return the normalized path which is usable in boto3.

    We need to make sure that any path that has to be used internally:
        - must not start with a '/'
        - must end with a '/'

    Also, if there's no path, we should always default to `/`.

    Args:
        path (string)

    Returns:
        string
    """

    if not (path is None or isinstance(path, basestring)):
        raise InvalidPathError

    if not path:
        return "/"

    # make sure the path never starts with a '/'
    path = path.lstrip('/')

    # make sure the path always ends with a '/'
    if not path.endswith('/'):
        path += '/'

    return path
