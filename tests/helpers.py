"""Fixtures to be used in tests."""

from __future__ import annotations

from boto3 import Session

DUMMY_BUCKET_NAME = "dummy-bucket"
DUMMY_ACCESS_KEY_ID = "dummy-key"
DUMMY_SECRET_ACCESS_KEY = "dummy-secret"


def generate_dummy_bucket() -> None:
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
    objects = {
        "index.js": b"console.log('hello')",
        "avatar.jpg": b"\xff\xd8\xff",
        "__init__.py": b"",
        "Makefile": b"test:\n\tpytest\n",
        "css/app.less": b"abcd { color: #111; }\n",
        "css/base.css": b"body { margin: 0; }\n",
        "js/vendor/angular.js": b"angular.module('demo', [])",
        "js/vendor/angular.min.js": b"angular.module('demo',[])",
        "js/vendor/latest/react.js": b"window.React = {}",
        "cache/foo.rb": b"puts 'hello'",
        "cache/staticfiles/latest/index.js": b"console.log('latest')",
        "cache/staticfiles/dummy.txt": b"dummy",
        "cache/staticfiles/logs.txt": b"logs",
        "empty/": b"",
    }

    for key, content in objects.items():
        s3.meta.client.put_object(Bucket=DUMMY_BUCKET_NAME, Key=key, Body=content)
