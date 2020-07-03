#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for core module."""

import json
from moto import mock_s3
from pytest import raises, fail
from six import string_types
import s3tree
from .helpers import (
    DUMMY_BUCKET_NAME,
    DUMMY_ACCESS_KEY_ID,
    DUMMY_SECRET_ACCESS_KEY,
    generate_dummy_bucket,
)


def test_s3tree_improperly_configured():
    with raises(s3tree.exceptions.ImproperlyConfiguredError):
        s3tree.S3Tree(bucket_name="foo")


def test_s3tree_work_with_global_config():
    s3tree.config.aws_access_key_id = "foo"
    s3tree.config.aws_secret_access_key = "bar"
    try:
        s3tree.S3Tree(bucket_name="foo")
    except s3tree.exceptions.ImproperlyConfiguredError:
        raise fail("Initialization failed with global config.")
    except Exception:
        pass


@mock_s3
def test_s3tree_tree_sanity():
    generate_dummy_bucket()
    tree = s3tree.S3Tree(
        bucket_name=DUMMY_BUCKET_NAME,
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        path="/",
    )
    # we're using some magic values for asserting tests here for the tree.
    # refer to helpers.generate_dummy_bucket to see the origin of these values.
    assert len(tree) == 7
    assert tree.num_directories == 3
    assert len(tree.directories) == 3
    assert tree.num_files == 4
    assert len(tree.files) == 4

    # the first object in the tree should be a directory called `css`
    assert isinstance(tree[0], s3tree.models.Directory)
    assert tree[0].name == "cache"

    # the last object in the tree should be a file called `Makefile`
    assert isinstance(tree[-1], s3tree.models.File)
    assert tree[-1].name == "index.js"


@mock_s3
def test_exception_when_bucket_not_found():
    with raises(s3tree.exceptions.BucketNotFound):
        s3tree.S3Tree(
            bucket_name=DUMMY_BUCKET_NAME,
            aws_access_key_id=DUMMY_ACCESS_KEY_ID,
            aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        )


@mock_s3
def test_exception_when_directory_not_found():
    generate_dummy_bucket()
    with raises(s3tree.exceptions.DirectoryNotFound):
        s3tree.S3Tree(
            bucket_name=DUMMY_BUCKET_NAME,
            aws_access_key_id=DUMMY_ACCESS_KEY_ID,
            aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
            path="/non-existent",
        )


@mock_s3
def test_directory_traversal():
    generate_dummy_bucket()
    tree = s3tree.S3Tree(
        bucket_name=DUMMY_BUCKET_NAME,
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        path="cache",
    )
    # get the first element, which is a directory
    directory = tree[0]

    child_tree = directory.get_tree()
    assert isinstance(child_tree, s3tree.S3Tree)
    assert len(child_tree) == 2


@mock_s3
def test_file_reads():
    generate_dummy_bucket()
    tree = s3tree.S3Tree(
        bucket_name=DUMMY_BUCKET_NAME,
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        path="css",
    )

    # the first element in this tree is a file
    dummy_file = tree[0]
    assert isinstance(dummy_file, s3tree.models.File)
    assert isinstance(dummy_file.read(), string_types)
    assert dummy_file.read().startswith("abcd")


@mock_s3
def test_tree_as_json_property():
    generate_dummy_bucket()
    tree = s3tree.S3Tree(
        bucket_name=DUMMY_BUCKET_NAME,
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
    )
    json_data = tree.as_json
    data = json.loads(json_data)
    assert isinstance(json_data, string_types)
    assert isinstance(data, list)
    assert len(data) == 7
