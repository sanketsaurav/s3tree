class ImproperlyConfiguredError(Exception):
    def __init__(self) -> None:
        message = """aws_access_key_id and aws_secret_access_key must be
        provided, either while creating an S3Tree object, or setting globally
        on s3tree module. Couldn't find either of them.
        """
        super().__init__(message)


class BucketNotFound(Exception):
    def __init__(self, bucket_name: str) -> None:
        message = f"Could not find the bucket: {bucket_name}"
        super().__init__(message)


class BucketAccessDenied(Exception):
    def __init__(self, bucket_name: str) -> None:
        message = f"Permission to access denied for the bucket: {bucket_name}"
        super().__init__(message)


class InvalidPathError(Exception):
    def __init__(self) -> None:
        message = "Invalid path provided. Path must be a string, or None."
        super().__init__(message)


class FileNotFound(Exception):
    def __init__(self, file_name: str) -> None:
        message = f"File could not be found: {file_name}"
        super().__init__(message)


class DirectoryNotFound(Exception):
    def __init__(self, dir_name: str) -> None:
        message = f"Directory could not be found: {dir_name}"
        super().__init__(message)
