#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for utils."""

import pytest
from s3tree.exceptions import InvalidPathError
from s3tree.utils import normalize_path


def test_normalize_path_not_a_string():
    with pytest.raises(InvalidPathError):
        normalize_path(42)


def test_normalize_path_none():
    assert normalize_path(None) == '/'


def test_normalize_path():
    assert normalize_path('foo/bar/baz') == 'foo/bar/baz/'
    assert normalize_path('/dummy/') == 'dummy/'
