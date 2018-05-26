#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for models."""
import datetime
import json
from dateutil.tz import tzutc
import mock
import pytest
from s3tree.models import Directory, File
from s3tree.core import S3Tree


@pytest.fixture
def directory_data():
    return {u'Prefix': 'admin/img/gis/'}


@pytest.fixture
def file_data():
    return {u'ETag': '"2152fd3b4a4dd92fef70a86e50e1453b"',
            u'Key': 'admin/img/tooltag-add.png',
            u'LastModified': datetime.datetime(
                2018, 3, 16, 13, 25, 59, tzinfo=tzutc()
            ),
            u'Size': 2048,
            u'StorageClass': 'STANDARD'}


@pytest.fixture
def s3tree():
    return mock.MagicMock(spec=S3Tree)


def test_directory_class(directory_data, s3tree):
    # create a new directory from data
    directory = Directory(directory_data, s3tree)
    assert directory.path == 'admin/img/gis/'
    assert directory.name == 'gis'
    assert str(directory) == 'gis'


def test_directory_as_dict_property(directory_data, s3tree):
    directory = Directory(directory_data, s3tree)
    orig_data = dict(name='gis', path='admin/img/gis/')
    data = json.loads(directory.as_json)
    assert data == orig_data
    assert directory.as_dict == orig_data


def test_file_class(file_data, s3tree):
    # create a new file from data
    file_obj = File(file_data, s3tree)
    assert str(file_obj) == 'tooltag-add.png'
    assert file_obj.size == '2 KB'
    assert file_obj.name == 'tooltag-add.png'
    assert file_obj.path == 'admin/img/tooltag-add.png'
    assert file_obj.size_in_bytes == 2048


def test_file_as_dict_property(file_data, s3tree):
    file_obj = File(file_data, s3tree)
    orig_data = dict(name='tooltag-add.png',
                     path='admin/img/tooltag-add.png',
                     etag='"2152fd3b4a4dd92fef70a86e50e1453b"',
                     size_in_bytes=2048,
                     size='2 KB',
                     last_modified='2018-03-16T13:25:59+00:00')
    data = json.loads(file_obj.as_json)
    assert data == orig_data
    assert file_obj.as_dict == orig_data
