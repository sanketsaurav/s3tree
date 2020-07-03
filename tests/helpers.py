#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fixtures to be used in tests."""
from boto3 import Session
import random
import string

DUMMY_BUCKET_NAME = "dummy-bucket"
DUMMY_ACCESS_KEY_ID = "dummy-key"
DUMMY_SECRET_ACCESS_KEY = "dummy-secret"


def generate_dummy_bucket():

    session = Session(
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
    )

    s3 = session.resource("s3", region_name="us-east-1")

    # create a bucket
    s3.create_bucket(Bucket=DUMMY_BUCKET_NAME)

    # create some objects in this bucket
    # the root contain 7 objects: 4 files and 3 directories
    # the first entry in the tree should be the directory `cache`, since boto3
    # returns the values sorted alphabetically. The last object should be the
    # file called `index.js`.
    files = (
        "index.js",
        "avatar.jpg",
        "__init__.py",
        "Makefile",
        "css/app.less",
        "css/base.css",
        "js/vendor/angular.js",
        "js/vendor/angular.min.js",
        "js/vendor/latest/react.js",
        "cache/foo.rb",
        "cache/staticfiles/latest/index.js" "cache/staticfiles/dummy.txt",
        "cache/staticfiles/logs.txt",
    )

    for file in files:
        content = string.ascii_letters * random.randint(1, 10)
        s3.meta.client.put_object(Bucket=DUMMY_BUCKET_NAME, Key=file, Body=content)
