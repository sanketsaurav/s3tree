#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for utils."""

import pytest
from s3tree.exceptions import InvalidPathError
from s3tree.utils import normalize_path, humanize_file_size


def test_normalize_path_not_a_string():
    with pytest.raises(InvalidPathError):
        normalize_path(42)


def test_normalize_path_none():
    assert normalize_path(None) == ''


def test_normalize_path_root():
    assert normalize_path('/') == ''


def test_normalize_path():
    assert normalize_path('foo/bar/baz') == 'foo/bar/baz/'
    assert normalize_path('/dummy/') == 'dummy/'


def test_humanize_file_size():
    mapping = (
        (133, '133 bytes'),
        (1024, '1 KB'),
        (2 * 1024 * 1024, '2 MB'),
        (1700, '1.66 KB'),
        (1600000000, '1.49 GB')
    )

    for k, v in mapping:
        assert humanize_file_size(k) == v
