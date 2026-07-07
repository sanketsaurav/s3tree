"""Tests for the core S3Tree API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

import s3tree
import s3tree.exceptions

from .helpers import (
    DUMMY_ACCESS_KEY_ID,
    DUMMY_BUCKET_NAME,
    DUMMY_SECRET_ACCESS_KEY,
    generate_dummy_bucket,
)


@mock_aws
def test_s3tree_uses_boto3_credential_chain_without_explicit_keys() -> None:
    generate_dummy_bucket()

    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME)

    assert len(tree) == 8
    assert tree.num_directories == 4
    assert tree.num_files == 4


def test_s3tree_rejects_path_and_prefix_together() -> None:
    with pytest.raises(ValueError, match="Pass either path or prefix"):
        s3tree.S3Tree(
            bucket_name=DUMMY_BUCKET_NAME,
            path="assets",
            prefix="assets",
            validate_bucket=False,
        )


@mock_aws
def test_s3tree_still_accepts_explicit_credentials() -> None:
    generate_dummy_bucket()

    tree = s3tree.S3Tree(
        bucket_name=DUMMY_BUCKET_NAME,
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        path="/",
    )

    assert isinstance(tree[0], s3tree.Directory)
    assert tree[0].name == "cache"
    assert isinstance(tree[-1], s3tree.File)
    assert tree[-1].name == "index.js"


@mock_aws
def test_exception_when_bucket_not_found() -> None:
    with pytest.raises(s3tree.exceptions.BucketNotFound):
        s3tree.S3Tree(
            bucket_name=DUMMY_BUCKET_NAME,
            aws_access_key_id=DUMMY_ACCESS_KEY_ID,
            aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
        )


@mock_aws
def test_exception_when_directory_not_found() -> None:
    generate_dummy_bucket()

    with pytest.raises(s3tree.exceptions.DirectoryNotFound):
        s3tree.S3Tree(
            bucket_name=DUMMY_BUCKET_NAME,
            aws_access_key_id=DUMMY_ACCESS_KEY_ID,
            aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
            path="/non-existent",
        )


@mock_aws
def test_empty_directory_marker_is_valid_empty_tree() -> None:
    generate_dummy_bucket()

    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME, prefix="empty")

    assert len(tree) == 0
    assert tree.num_directories == 0
    assert tree.num_files == 0


@mock_aws
def test_directory_traversal() -> None:
    generate_dummy_bucket()
    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME, path="cache")

    directory = tree.directories[0]
    child_tree = directory.get_tree()

    assert isinstance(child_tree, s3tree.S3Tree)
    assert child_tree.prefix == "cache/staticfiles/"
    assert len(child_tree) == 3


@mock_aws
def test_file_reads_text_and_bytes() -> None:
    generate_dummy_bucket()
    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME, path="css")

    dummy_file = tree.files[0]

    assert isinstance(dummy_file.read_text(), str)
    assert dummy_file.read_text().startswith("abcd")
    assert dummy_file.read_bytes().startswith(b"abcd")
    assert dummy_file.read().startswith("abcd")


@mock_aws
def test_walk_and_recursive_file_iteration() -> None:
    generate_dummy_bucket()
    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME)

    walked = list(tree.walk())
    recursive_files = list(tree.iter_files(recursive=True))
    recursive_directories = list(tree.iter_directories(recursive=True))

    assert any(entry.path == "cache/staticfiles/latest/" for entry in walked)
    assert any(
        file.path == "cache/staticfiles/latest/index.js" for file in recursive_files
    )
    assert any(
        directory.path == "cache/staticfiles/latest/"
        for directory in recursive_directories
    )


@mock_aws
def test_tree_json_representation_is_ui_ready() -> None:
    generate_dummy_bucket()
    tree = s3tree.S3Tree(bucket_name=DUMMY_BUCKET_NAME)

    data = json.loads(tree.to_json())

    assert data["bucket"] == DUMMY_BUCKET_NAME
    assert data["prefix"] == ""
    assert data["num_directories"] == 4
    assert data["num_files"] == 4
    assert data["children"][0]["kind"] == "directory"
    assert tree.as_dict == tree.to_dict()
    assert json.loads(tree.as_json) == data


@mock_aws
def test_listing_uses_paginator_across_more_than_one_page() -> None:
    generate_dummy_bucket()
    session = boto3.Session(
        aws_access_key_id=DUMMY_ACCESS_KEY_ID,
        aws_secret_access_key=DUMMY_SECRET_ACCESS_KEY,
    )
    client = session.client("s3", region_name="us-east-1")
    for index in range(1205):
        client.put_object(
            Bucket=DUMMY_BUCKET_NAME,
            Key=f"many/file-{index:04d}.txt",
            Body=b"x",
        )

    tree = s3tree.S3Tree.from_client(
        bucket_name=DUMMY_BUCKET_NAME,
        client=client,
        prefix="many",
        page_size=100,
        validate_bucket=False,
    )

    assert len(tree.files) == 1205


def _client_error(code: str, status: int) -> ClientError:
    return ClientError(
        cast(Any, {
            "Error": {"Code": code, "Message": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }),
        "ListObjectsV2",
    )


@dataclass
class FakePageIterator:
    response: dict[str, Any]

    def build_full_result(self) -> dict[str, Any]:
        return self.response


@dataclass
class FakePaginator:
    client: FakeS3Client

    def paginate(self, **kwargs: Any) -> FakePageIterator:
        self.client.list_kwargs = kwargs
        if self.client.list_response is None:
            contents: list[dict[str, Any]] = []
            if kwargs["Prefix"]:
                contents.append({"Key": kwargs["Prefix"], "Size": 0})
            response = {
                "CommonPrefixes": [
                    {"Prefix": "duplicated/"},
                    {"Prefix": "duplicated/"},
                ],
                "Contents": contents,
            }
        else:
            response = dict(self.client.list_response)
        if self.client.next_token is not None:
            response["NextToken"] = self.client.next_token
        return FakePageIterator(response)


class FakeS3Client:
    def __init__(
        self,
        *,
        list_response: dict[str, Any] | None = None,
        next_token: str | None = None,
        head_object_response: dict[str, Any] | None = None,
    ) -> None:
        self.list_response = list_response
        self.next_token = next_token
        self.head_object_response = head_object_response
        self.list_kwargs: dict[str, Any] | None = None
        self.head_kwargs: dict[str, Any] | None = None
        self.head_object_kwargs: dict[str, Any] | None = None

    def get_paginator(self, operation_name: str) -> Any:
        assert operation_name == "list_objects_v2"
        return FakePaginator(self)

    def head_bucket(self, **kwargs: Any) -> None:
        self.head_kwargs = kwargs

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"Body": FakeBody()}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.head_object_kwargs = kwargs
        if self.head_object_response is None:
            return {}
        return self.head_object_response


class FakeBody:
    closed = False

    def read(self, amt: int | None = None) -> bytes:
        return b""

    def close(self) -> None:
        self.closed = True


class ErrorPaginator:
    def __init__(self, error: ClientError) -> None:
        self.error = error

    def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
        raise self.error


class ErrorS3Client(FakeS3Client):
    def __init__(self, error: ClientError) -> None:
        super().__init__()
        self.error = error

    def get_paginator(self, operation_name: str) -> ErrorPaginator:
        assert operation_name == "list_objects_v2"
        return ErrorPaginator(self.error)


def test_s3_compatible_clients_can_be_injected() -> None:
    client = FakeS3Client()

    tree = s3tree.S3Tree.from_client(
        bucket_name="r2-bucket",
        client=client,
        prefix="datasets",
        page_size=5,
        max_items=10,
        request_payer="requester",
        expected_bucket_owner="123456789012",
    )

    assert tree.prefix == "datasets/"
    assert [directory.path for directory in tree.directories] == ["duplicated/"]
    assert client.head_kwargs == {
        "Bucket": "r2-bucket",
        "RequestPayer": "requester",
        "ExpectedBucketOwner": "123456789012",
    }
    assert client.list_kwargs == {
        "Bucket": "r2-bucket",
        "Delimiter": "/",
        "Prefix": "datasets/",
        "RequestPayer": "requester",
        "ExpectedBucketOwner": "123456789012",
        "PaginationConfig": {"PageSize": 5, "MaxItems": 10},
    }


def test_from_uri_parses_s3_bucket_and_prefix() -> None:
    client = FakeS3Client()

    tree = s3tree.S3Tree.from_uri(
        "s3://r2-bucket/datasets%20v1",
        client=client,
        validate_bucket=False,
    )

    assert tree.bucket_name == "r2-bucket"
    assert tree.prefix == "datasets v1/"
    assert client.list_kwargs == {
        "Bucket": "r2-bucket",
        "Delimiter": "/",
        "Prefix": "datasets v1/",
    }


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/bucket/prefix",
        "s3:///prefix",
        "s3://bucket/prefix?versionId=1",
        "s3://bucket/prefix#objects",
        "s3://bucket/prefix;param",
    ],
)
def test_from_uri_rejects_non_tree_uris(uri: str) -> None:
    with pytest.raises(ValueError, match="S3Tree URIs"):
        s3tree.S3Tree.from_uri(uri, validate_bucket=False)


def test_fetch_page_uses_cursor_and_serializes_page() -> None:
    client = FakeS3Client(
        list_response={
            "CommonPrefixes": [{"Prefix": "datasets/images/"}],
            "Contents": [
                {
                    "Key": "datasets/index.json",
                    "Size": 16,
                    "StorageClass": "STANDARD",
                },
            ],
        },
        next_token="cursor-2",
    )

    page = s3tree.S3Tree.fetch_page(
        "r2-bucket",
        client=client,
        prefix="datasets",
        starting_token="cursor-1",
        page_size=1,
        validate_bucket=False,
    )
    payload = page.to_dict()

    assert isinstance(page, s3tree.S3TreePage)
    assert len(page) == 2
    assert page[0].path == "datasets/images/"
    assert [entry.path for entry in page[:]] == [
        "datasets/images/",
        "datasets/index.json",
    ]
    assert page.has_more is True
    assert page.next_token == "cursor-2"
    assert page.num_directories == 1
    assert page.num_files == 1
    assert payload["next_token"] == "cursor-2"
    assert payload["has_more"] is True
    assert json.loads(page.to_json()) == payload
    assert page.as_dict == payload
    assert json.loads(page.as_json) == payload
    assert client.list_kwargs == {
        "Bucket": "r2-bucket",
        "Delimiter": "/",
        "Prefix": "datasets/",
        "PaginationConfig": {
            "PageSize": 1,
            "MaxItems": 1,
            "StartingToken": "cursor-1",
        },
    }


def test_fetch_page_defaults_to_a_bounded_page() -> None:
    client = FakeS3Client()

    page = s3tree.S3Tree.fetch_page(
        "r2-bucket",
        client=client,
        validate_bucket=False,
    )

    assert page.path == ""
    assert page.has_more is False
    assert client.list_kwargs == {
        "Bucket": "r2-bucket",
        "Delimiter": "/",
        "Prefix": "",
        "PaginationConfig": {"MaxItems": 100},
    }


def test_fetch_page_from_uri_uses_uri_prefix() -> None:
    client = FakeS3Client(next_token="next")

    page = s3tree.S3Tree.fetch_page_from_uri(
        "s3://r2-bucket/datasets",
        client=client,
        validate_bucket=False,
        max_items=2,
    )

    assert page.bucket_name == "r2-bucket"
    assert page.prefix == "datasets/"
    assert page.has_more is True
    assert client.list_kwargs == {
        "Bucket": "r2-bucket",
        "Delimiter": "/",
        "Prefix": "datasets/",
        "PaginationConfig": {"MaxItems": 2},
    }


def test_metadata_enrichment_loads_head_object_fields() -> None:
    client = FakeS3Client(
        list_response={
            "Contents": [
                {
                    "Key": "datasets/events.jsonl",
                    "Size": 10,
                    "ChecksumAlgorithm": ["SHA256"],
                    "ChecksumType": "FULL_OBJECT",
                    "RestoreStatus": {"IsRestoreInProgress": False},
                },
            ],
        },
        head_object_response={
            "ContentType": "application/x-jsonlines",
            "Metadata": {"source": "r2"},
            "VersionId": "version-1",
            "ContentLength": 128,
        },
    )

    tree = s3tree.S3Tree.from_client(
        bucket_name="r2-bucket",
        client=client,
        prefix="datasets",
        validate_bucket=False,
        enrich_metadata=True,
    )
    file_obj = tree.files[0]

    assert file_obj.content_type == "application/x-jsonlines"
    assert file_obj.metadata == {"source": "r2"}
    assert file_obj.version_id == "version-1"
    assert file_obj.size_in_bytes == 128
    assert file_obj.checksum_algorithm == ("SHA256",)
    assert file_obj.checksum_type == "FULL_OBJECT"
    assert file_obj.restore_status == {"IsRestoreInProgress": False}
    assert client.head_object_kwargs == {
        "Bucket": "r2-bucket",
        "Key": "datasets/events.jsonl",
    }


def test_list_errors_are_mapped_to_access_denied() -> None:
    client = ErrorS3Client(_client_error("AccessDenied", 403))

    with pytest.raises(s3tree.exceptions.BucketAccessDenied):
        s3tree.S3Tree.from_client(
            bucket_name="r2-bucket",
            client=client,
            validate_bucket=False,
        )


def test_unknown_client_errors_are_preserved() -> None:
    client = ErrorS3Client(_client_error("SlowDown", 503))

    with pytest.raises(ClientError, match="SlowDown"):
        s3tree.S3Tree.from_client(
            bucket_name="r2-bucket",
            client=client,
            validate_bucket=False,
        )


def test_endpoint_url_and_region_are_passed_to_boto3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    client = FakeS3Client()

    class FakeSession:
        def __init__(self, **kwargs: Any) -> None:
            calls["session"] = kwargs

        def client(self, **kwargs: Any) -> FakeS3Client:
            calls["client"] = kwargs
            return client

    monkeypatch.setattr(s3tree.core.boto3, "Session", FakeSession)

    s3tree.S3Tree(
        bucket_name="r2-bucket",
        endpoint_url="https://account-id.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id="access-key",
        aws_secret_access_key="secret-key",
        verify=False,
    )

    assert calls["session"] == {
        "profile_name": None,
        "region_name": "auto",
        "aws_access_key_id": "access-key",
        "aws_secret_access_key": "secret-key",
        "aws_session_token": None,
    }
    assert calls["client"] == {
        "service_name": "s3",
        "region_name": "auto",
        "endpoint_url": "https://account-id.r2.cloudflarestorage.com",
        "verify": False,
    }
