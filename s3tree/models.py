#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module contains the model objects that are used to represent
trees and files in S3Tree."""
import os
from future.utils import python_2_unicode_compatible
from .utils import humanize_file_size
from .exceptions import FileNotFound


@python_2_unicode_compatible
class Directory(object):
    """
    Iterable container that represents a directory.
    """

    def __init__(self, data, s3tree):
        self.path = data.get('Prefix')
        self.s3tree = s3tree

    @property
    def name(self):
        return os.path.basename(self.path.rstrip('/'))

    def __str__(self):
        return self.name

    def get_tree(self):
        return self.s3tree.__class__(
            bucket_name=self.s3tree.bucket_name, path=self.path,
            aws_access_key_id=self.s3tree._access_key,
            aws_secret_access_key=self.s3tree._secret_key
        )


@python_2_unicode_compatible
class File(object):
    """Object that represents an individual file."""

    def __init__(self, data, s3tree):
        # public attributes
        self.path = data.get('Key')
        self.etag = data.get('ETag')
        self.last_modified = data.get('LastModified')
        self.size_in_bytes = data.get('Size')
        self.storage_class = data.get('StorageClass')

        # private attributes
        self.__s3tree = s3tree

    @property
    def size(self):
        """Human readable size of this file."""
        return humanize_file_size(self.size_in_bytes)

    @property
    def name(self):
        """File name of this file."""
        return os.path.basename(self.path)

    def read(self):
        """Read the contents of this file. This method returns a string."""
        try:
            return self.__s3tree.client.get_object(
                Bucket=self.__s3tree.bucket_name,
                Key=self.path)['Body'].read().decode("utf-8")
        except self.__s3tree.client.exceptions.NoSuchKey:
            raise FileNotFound(self.path)

    def __str__(self):
        return self.name
