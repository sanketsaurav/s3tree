#!/usr/bin/env python
# -*- coding: utf-8 -*-


class BucketNotFound(Exception):
    def __init__(self, bucket_name):
        message = "Could not find the bucket: {}".format(bucket_name)
        super(BucketNotFound, self).__init__(message)


class BucketAccessDenied(Exception):
    def __init__(self, bucket_name):
        message = "Permission to access denied for the bucket: {}".format(
            bucket_name
        )
        super(BucketAccessDenied, self).__init__(message)


class InvalidPathError(Exception):
    def __init__(self):
        message = "Invalid path provided. Path must be a string, or None."
        super(InvalidPathError, self).__init__(message)


class FileNotFound(Exception):
    def __init__(self, file_name):
        message = "File could not be found: {}".format(file_name)
        super(FileNotFound, self).__init__(message)


class DirectoryNotFound(Exception):
    def __init__(self, dir_name):
        message = "Directory could not be found: {}".format(dir_name)
        super(DirectoryNotFound, self).__init__(message)
