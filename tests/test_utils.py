"""Tests for utils."""

from typing import cast

import pytest

from s3tree.exceptions import InvalidPathError
from s3tree.utils import humanize_file_size, normalize_path


def test_normalize_path_not_a_string() -> None:
    with pytest.raises(InvalidPathError):
        normalize_path(cast(str | None, 42))


def test_normalize_path_none() -> None:
    assert normalize_path(None) == ""


def test_normalize_path_root() -> None:
    assert normalize_path("/") == ""


def test_normalize_path() -> None:
    assert normalize_path("foo/bar/baz") == "foo/bar/baz/"
    assert normalize_path("/dummy/") == "dummy/"


def test_humanize_file_size() -> None:
    mapping = (
        (133, "133 bytes"),
        (1024, "1 KB"),
        (2 * 1024 * 1024, "2 MB"),
        (1700, "1.66 KB"),
        (1600000000, "1.49 GB"),
    )

    for k, v in mapping:
        assert humanize_file_size(k) == v
