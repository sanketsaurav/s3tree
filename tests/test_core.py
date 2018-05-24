#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for core module."""

from pytest import raises, fail
import s3tree


def test_s3tree_improperly_configured():
    with raises(s3tree.exceptions.ImproperlyConfiguredError):
        s3tree.S3Tree(bucket_name='foo')


def test_s3tree_work_with_global_config():
    s3tree.config.aws_access_key_id = 'foo'
    s3tree.config.aws_secret_access_key = 'bar'
    try:
        s3tree.S3Tree(bucket_name='foo')
    except s3tree.exceptions.ImproperlyConfiguredError:
        raise fail('Initialization failed with global config.')
    except Exception:
        pass
