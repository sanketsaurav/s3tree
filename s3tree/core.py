#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
from boto3 import Session
from botocore.exceptions import ClientError

from .exceptions import BucketAccessDenied, BucketNotFound, DirectoryNotFound
from .utils import normalize_path


class S3Tree(object):
    """
    Primary entry-point to use S3Tree.

    This creates an object with the provided base path as the directory root.
    It exposes methods to traverse the tree beneath that path, and to
    get individual files.

    Args:
        bucket_name (str): Name of the S3 bucket.
        aws_access_key_id (str): The AWS access key ID.
        aws_secret_access_key (str): The AWS secret access key.
        base_path (:object: str, optional): The key of the path which should
            be treated as the base of this tree. Defaults `None`, which
            represents the root of this bucket.
    """

    BOTO3_S3_RESOURCE_ID = 's3'

    KEY_DELIMITER = '/'

    def __init__(self, bucket_name, aws_access_key_id,
                 aws_secret_access_key, base_path=None):
        # create a session using the creds
        session = Session(aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key)

        # create an S3 resource
        self.s3 = session.resource(self.BOTO3_S3_RESOURCE_ID)
        self.client = self.s3.meta.client

        # ensure that the bucket exists, and then set the bucket name
        self.__ensure_bucket_exists()
        self.bucket_name = bucket_name

        # set the base path
        self.base_path = base_path

    def listdir(self, path='/'):
        """
        Returns a list of files and directories present under the given path.

        The path specified could be a single directory, or multiple directory
        traversal. If no path is passed, the base path is taken.

        Usage:
            >>> tree = S3Tree()
            >>> tree.listdir('/css')
            # Returns the tree inside `css` key from the base of the bucket
            >>> tree.listdir('/static/js/services')
            # Returns the tree inside `static/js/services` path from the
            # base of the bucket

        Args:
            path (string): The path to list the files and directories of.
                Defaults to '/'.
        """

        full_path = normalize_path(os.path.join(self.base_path, path))

        # get tree
        tree_data = self.client.list_objects_v2(
            Bucket=self.bucket_name, Delimiter=self.KEY_DELIMITER,
            Prefix=full_path)

        # if this directory is empty, raise an error
        if not tree_data.get('KeyCount'):
            raise DirectoryNotFound(full_path)

        # otherwise, return the tree
        else:
            pass

    def getfile(self, path):
        """Returns the file at the given path.

        Usage:
            >>> tree = S3Tree()
            >>> tree.getfile('/static/bumble.js')

        Args:
            path (string): The path of the file.
        """
        pass

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
                raise BucketNotFound

            elif error_code == 403:
                raise BucketAccessDenied

            else:
                raise exc
