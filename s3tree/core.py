#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from boto3 import Session
from botocore.exceptions import ClientError
from collections import Sequence

from . import config
from .exceptions import (BucketAccessDenied, BucketNotFound, DirectoryNotFound,
                         ImproperlyConfiguredError)
from .models import Directory, File
from .utils import normalize_path


class S3Tree(Sequence):
    """
    Create an S3Tree object to access the tree at the given path.

    You can iterate upon this object to access directories and files in this
    tree.

    Usage:
        >>> tree = S3Tree(bucket_name='demo', path='/css')
        # Returns the tree inside `css` key from the base of the bucket
        >>> tree = S3Tree(bucket_name='demo', path='/static/js/services')
        # Returns the tree inside `static/js/services` path from the
        # base of the bucket. The leading '/' is optional.

    Args:
        bucket_name (str): Name of the S3 bucket.
        path (:object: str, optional): The key of the path which should
            be treated as the base of this tree. Defaults `/`, which
            represents the root of this bucket.
        aws_access_key_id (:object: str, optional): The AWS access key ID.
        aws_secret_access_key (:object: str, optional): The AWS secret
            access key.
    """

    BOTO3_S3_RESOURCE_ID = 's3'

    KEY_DELIMITER = '/'

    def __init__(self, bucket_name, path=None, aws_access_key_id=None,
                 aws_secret_access_key=None):
        # try to get the access key and secret key either from this object's
        # init, or from the global config.
        self._access_key = aws_access_key_id or config.aws_access_key_id
        self._secret_key = (aws_secret_access_key or
                            config.aws_secret_access_key)

        if not (self._access_key and self._secret_key):
            raise ImproperlyConfiguredError

        # create a session using the credentials
        session = Session(aws_access_key_id=self._access_key,
                          aws_secret_access_key=self._secret_key)

        # create an S3 resource
        self.s3 = session.resource(self.BOTO3_S3_RESOURCE_ID)
        self.client = self.s3.meta.client

        # ensure that the bucket exists, and then set the bucket name
        self.__ensure_bucket_exists(bucket_name)
        self.bucket_name = bucket_name

        # set the base path
        self.path = normalize_path(path)

        # set containers
        self.directories = []
        self.files = []

        # get the base tree and prepare the iterable
        self.__tree = self.__fetch_tree()

    def __getitem__(self, index):
        return self.__tree[index]

    def __len__(self):
        return len(self.__tree)

    def __fetch_tree(self):
        # retrieve the tree at the current path
        tree = self.client.list_objects_v2(
            Bucket=self.bucket_name, Delimiter=self.KEY_DELIMITER,
            Prefix=self.path)

        tree_size = tree.get('KeyCount')

        # if the current tree is empty and we are not accessing the bucket
        # root, throw an error since this directory does not exist.
        if not tree_size and self.path != self.KEY_DELIMITER:
            raise DirectoryNotFound(self.path)

        # otherwise, prepare the tree and return the list
        else:
            return self.__prepare_tree(tree)

    def __prepare_tree(self, data):
        """Takes the tree data and returns a list representing the tree object.
        """
        directories = data.get('CommonPrefixes', [])
        files = data.get('Contents', [])

        for d in directories:
            self.directories.append(Directory(d, self))

        for f in files:
            self.files.append(File(f, self))

        return self.directories + self.files

    def __ensure_bucket_exists(self, bucket_name):
        """Check if the bucket exists and the credentials provided have
        access to it. Otherwise, raise a proper exception.
        """

        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError as exc:
            # check the error code in the exception and raise a proper
            # exception
            error_code = int(exc.response['Error']['Code'])

            if error_code == 404:
                raise BucketNotFound(bucket_name)

            elif error_code == 403:
                raise BucketAccessDenied(bucket_name)

            else:
                raise exc

    @property
    def num_files(self):
        """Returns the number of files in this tree."""
        return len(self.files)

    @property
    def num_directories(self):
        """Returns the number of directories in this tree."""
        return len(self.directories)
