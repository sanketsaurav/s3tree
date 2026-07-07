"""Tests for model objects."""

from __future__ import annotations

import datetime
import json
from typing import Any, cast

import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc

from s3tree.core import S3Tree
from s3tree.exceptions import FileNotFound
from s3tree.models import Directory, File


@pytest.fixture
def s3tree() -> S3Tree:
    class DummyTree:
        bucket_name = "dummy-bucket"
        delimiter = "/"

        def _spawn(self, path: str) -> tuple[str, str]:
            return self.bucket_name, path

    return cast(S3Tree, DummyTree())


@pytest.fixture
def directory_data() -> dict[str, object]:
    return {"Prefix": "admin/img/gis/"}


@pytest.fixture
def file_data() -> dict[str, object]:
    return {
        "ETag": '"2152fd3b4a4dd92fef70a86e50e1453b"',
        "Key": "admin/img/tooltag-add.png",
        "LastModified": datetime.datetime(2018, 3, 16, 13, 25, 59, tzinfo=tzutc()),
        "Size": 2048,
        "StorageClass": "STANDARD",
        "ChecksumAlgorithm": ["SHA256"],
        "ChecksumType": "FULL_OBJECT",
        "RestoreStatus": {"IsRestoreInProgress": False},
    }


def test_directory_class(
    directory_data: dict[str, object],
    s3tree: S3Tree,
) -> None:
    directory = Directory.from_api(directory_data, s3tree)

    assert directory.path == "admin/img/gis/"
    assert directory.prefix == "admin/img/gis/"
    assert directory.name == "gis"
    assert directory.bucket_name == "dummy-bucket"
    assert str(directory) == "gis"


def test_directory_serialization(
    directory_data: dict[str, object],
    s3tree: S3Tree,
) -> None:
    directory = Directory.from_api(directory_data, s3tree)
    expected = {
        "kind": "directory",
        "name": "gis",
        "path": "admin/img/gis/",
        "prefix": "admin/img/gis/",
    }

    assert json.loads(directory.to_json()) == expected
    assert json.loads(directory.as_json) == expected
    assert directory.as_dict == expected


def test_file_class(file_data: dict[str, object], s3tree: S3Tree) -> None:
    file_obj = File.from_api(file_data, s3tree)

    assert str(file_obj) == "tooltag-add.png"
    assert file_obj.size == "2 KB"
    assert file_obj.name == "tooltag-add.png"
    assert file_obj.path == "admin/img/tooltag-add.png"
    assert file_obj.key == "admin/img/tooltag-add.png"
    assert file_obj.size_in_bytes == 2048
    assert file_obj.content_type == "image/png"
    assert file_obj.file_type == "image"


def test_file_type_categories(s3tree: S3Tree) -> None:
    assert File(path="audio.mp3", s3tree=s3tree).file_type == "media"
    assert File(path="archive.json", s3tree=s3tree).file_type == "binary"


def test_file_serialization(file_data: dict[str, object], s3tree: S3Tree) -> None:
    file_obj = File.from_api(file_data, s3tree)
    expected = {
        "kind": "file",
        "name": "tooltag-add.png",
        "path": "admin/img/tooltag-add.png",
        "key": "admin/img/tooltag-add.png",
        "file_type": "image",
        "content_type": "image/png",
        "etag": '"2152fd3b4a4dd92fef70a86e50e1453b"',
        "storage_class": "STANDARD",
        "size_in_bytes": 2048,
        "size": "2 KB",
        "last_modified": "2018-03-16T13:25:59+00:00",
        "metadata": {},
        "version_id": None,
        "checksum_algorithm": ["SHA256"],
        "checksum_type": "FULL_OBJECT",
        "restore_status": {"IsRestoreInProgress": False},
    }

    assert json.loads(file_obj.to_json()) == expected
    assert json.loads(file_obj.as_json) == expected
    assert file_obj.as_dict == expected


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "GetObject")


class RaisingClient:
    def __init__(self, error: ClientError) -> None:
        self.error = error

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        raise self.error


class ReadingTree:
    bucket_name = "dummy-bucket"
    _request_options: dict[str, str] = {}

    def __init__(self, error: ClientError) -> None:
        self.client = RaisingClient(error)


def test_file_read_bytes_maps_missing_keys() -> None:
    tree = cast(S3Tree, ReadingTree(_client_error("NoSuchKey")))
    file_obj = File(path="missing.txt", s3tree=tree)

    with pytest.raises(FileNotFound):
        file_obj.read_bytes()


def test_file_read_bytes_preserves_unknown_client_errors() -> None:
    tree = cast(S3Tree, ReadingTree(_client_error("InternalError")))
    file_obj = File(path="broken.txt", s3tree=tree)

    with pytest.raises(ClientError, match="InternalError"):
        file_obj.read_bytes()


class ClosingBody:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0
        self.closed = False

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            chunk = self.data[self.offset :]
            self.offset = len(self.data)
            return chunk

        chunk = self.data[self.offset : self.offset + amt]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


class ObjectClient:
    def __init__(self, body: ClosingBody) -> None:
        self.body = body
        self.get_object_kwargs: dict[str, Any] | None = None

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self.get_object_kwargs = kwargs
        return {"Body": self.body}


class ObjectTree:
    bucket_name = "dummy-bucket"
    _request_options = {"RequestPayer": "requester"}

    def __init__(self, body: ClosingBody) -> None:
        self.client = ObjectClient(body)


def test_file_open_returns_streaming_body() -> None:
    body = ClosingBody(b"abcdef")
    tree = cast(S3Tree, ObjectTree(body))
    file_obj = File(path="objects/blob.bin", s3tree=tree)

    stream = file_obj.open()

    assert stream is body
    assert body.closed is False


def test_file_read_bytes_closes_streaming_body() -> None:
    body = ClosingBody(b"abcdef")
    tree_obj = ObjectTree(body)
    tree = cast(S3Tree, tree_obj)
    file_obj = File(path="objects/blob.bin", s3tree=tree)

    assert file_obj.read_bytes() == b"abcdef"
    assert body.closed is True
    assert tree_obj.client.get_object_kwargs == {
        "Bucket": "dummy-bucket",
        "Key": "objects/blob.bin",
        "RequestPayer": "requester",
    }


def test_file_iter_chunks_streams_and_closes_body() -> None:
    body = ClosingBody(b"abcdef")
    tree = cast(S3Tree, ObjectTree(body))
    file_obj = File(path="objects/blob.bin", s3tree=tree)

    assert list(file_obj.iter_chunks(chunk_size=2)) == [b"ab", b"cd", b"ef"]
    assert body.closed is True


def test_file_iter_chunks_rejects_invalid_chunk_size() -> None:
    body = ClosingBody(b"abcdef")
    tree = cast(S3Tree, ObjectTree(body))
    file_obj = File(path="objects/blob.bin", s3tree=tree)

    with pytest.raises(ValueError, match="chunk_size"):
        list(file_obj.iter_chunks(chunk_size=0))

    assert body.closed is False


class MetadataClient:
    def __init__(
        self,
        response: dict[str, Any] | None = None,
        error: ClientError | None = None,
    ) -> None:
        self.response = response or {}
        self.error = error
        self.head_object_kwargs: dict[str, Any] | None = None

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.head_object_kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class MetadataTree:
    bucket_name = "dummy-bucket"
    _request_options = {"ExpectedBucketOwner": "123456789012"}

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        error: ClientError | None = None,
    ) -> None:
        self.client = MetadataClient(response=response, error=error)


def test_file_load_metadata_returns_enriched_copy() -> None:
    response = {
        "ETag": '"metadata-etag"',
        "LastModified": datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=tzutc()),
        "ContentType": "application/json",
        "Metadata": {"source": "cloudflare-r2"},
        "VersionId": "version-1",
        "ContentLength": 512,
        "StorageClass": "STANDARD_IA",
        "ChecksumAlgorithm": ["SHA1"],
        "ChecksumType": "COMPOSITE",
        "RestoreStatus": {"IsRestoreInProgress": True},
    }
    tree_obj = MetadataTree(response=response)
    tree = cast(S3Tree, tree_obj)
    file_obj = File(path="objects/events", s3tree=tree, size_in_bytes=12)

    loaded = file_obj.load_metadata()

    assert loaded is not file_obj
    assert loaded.content_type == "application/json"
    assert loaded.file_type == "binary"
    assert loaded.metadata == {"source": "cloudflare-r2"}
    assert loaded.version_id == "version-1"
    assert loaded.size_in_bytes == 512
    assert loaded.etag == '"metadata-etag"'
    assert loaded.last_modified == datetime.datetime(
        2026,
        1,
        2,
        3,
        4,
        5,
        tzinfo=tzutc(),
    )
    assert loaded.storage_class == "STANDARD_IA"
    assert loaded.checksum_algorithm == ("SHA1",)
    assert loaded.checksum_type == "COMPOSITE"
    assert loaded.restore_status == {"IsRestoreInProgress": True}
    assert file_obj.metadata == {}
    assert tree_obj.client.head_object_kwargs == {
        "Bucket": "dummy-bucket",
        "Key": "objects/events",
        "ExpectedBucketOwner": "123456789012",
    }


def test_file_load_metadata_maps_missing_keys() -> None:
    tree = cast(S3Tree, MetadataTree(error=_client_error("NotFound")))
    file_obj = File(path="missing.txt", s3tree=tree)

    with pytest.raises(FileNotFound):
        file_obj.load_metadata()


def test_file_load_metadata_preserves_unknown_client_errors() -> None:
    tree = cast(S3Tree, MetadataTree(error=_client_error("InternalError")))
    file_obj = File(path="broken.txt", s3tree=tree)

    with pytest.raises(ClientError, match="InternalError"):
        file_obj.load_metadata()
