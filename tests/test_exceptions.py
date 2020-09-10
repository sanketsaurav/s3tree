from pytest import raises

from s3tree.exceptions import (BucketAccessDenied, BucketNotFound,
                               DirectoryNotFound, FileNotFound,
                               ImproperlyConfiguredError, InvalidPathError)


def test_improperly_configured_error_exc():
    with raises(ImproperlyConfiguredError) as exc:
        raise ImproperlyConfiguredError

    assert (
        str(exc.value)
        == """aws_access_key_id and aws_secret_access_key must be
        provided, either while creating an S3Tree object, or setting globally
        on s3tree module. Couldn't find either of them.
        """
    )


def test_bucket_not_found_exc():
    with raises(BucketNotFound) as exc:
        raise BucketNotFound("dummy")

    assert str(exc.value) == "Could not find the bucket: dummy"


def test_bucket_access_denied_exc():
    with raises(BucketAccessDenied) as exc:
        raise BucketAccessDenied("dummy")

    assert str(exc.value) == ("Permission to access denied for the" " bucket: dummy")


def test_invalid_path_error_exc():
    with raises(InvalidPathError) as exc:
        raise InvalidPathError

    assert str(exc.value) == (
        "Invalid path provided." " Path must be a string, or None."
    )


def test_file_not_found_exc():
    with raises(FileNotFound) as exc:
        raise FileNotFound("foo/bar.py")

    assert str(exc.value) == "File could not be found: foo/bar.py"


def test_directory_not_found_exc():
    with raises(DirectoryNotFound) as exc:
        raise DirectoryNotFound("foo/bar")

    assert str(exc.value) == "Directory could not be found: foo/bar"
