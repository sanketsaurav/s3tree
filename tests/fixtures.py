#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fixtures to be used in tests."""
import boto3
import pytest
import random
import string
from moto import mock_s3

DUMMY_BUCKET_NAME = 'dummy-bucket'


@pytest.fixture
@mock_s3
def s3_bucket():
    s3 = boto3.resource('s3', region_name='us-east-1')

    # create a bucket
    s3.create_bucket(Bucket=DUMMY_BUCKET_NAME)

    # create some objects in this bucket
    files = (
        'index.js', 'avatar.jpg', '__init__.py', 'Makefile',
        'css/app.less', 'css/base.css', 'js/vendor/angular.js',
        'js/vendor/angular.min.js', 'js/vendor/latest/react.js',
        'cache/staticfiles/latest/index.js'
    )

    for file in files:
        content = string.ascii_letters * random.randint(1, 10)
        s3.put_object(Bucket=DUMMY_BUCKET_NAME, Key=file,
                      Body=b'{}'.format(content))

