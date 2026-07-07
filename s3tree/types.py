"""Shared typed structures for s3tree."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypedDict

NodeKind = Literal["directory", "file"]


class DirectoryDict(TypedDict):
    kind: Literal["directory"]
    name: str
    path: str
    prefix: str


class FileDict(TypedDict):
    kind: Literal["file"]
    name: str
    path: str
    key: str
    etag: str | None
    last_modified: str | None
    size: str
    size_in_bytes: int
    storage_class: str | None
    content_type: str | None
    file_type: str
    metadata: dict[str, str]
    version_id: str | None
    checksum_algorithm: list[str]
    checksum_type: str | None
    restore_status: dict[str, Any] | None


TreeEntryDict = DirectoryDict | FileDict


class TreeDict(TypedDict):
    bucket: str
    prefix: str
    path: str
    delimiter: str
    num_directories: int
    num_files: int
    children: list[TreeEntryDict]


class TreePageDict(TypedDict):
    bucket: str
    prefix: str
    path: str
    delimiter: str
    num_directories: int
    num_files: int
    next_token: str | None
    has_more: bool
    children: list[TreeEntryDict]


class BodyStream(Protocol):
    def read(self, amt: int | None = None) -> bytes:
        ...

    def close(self) -> None:
        ...


class S3Client(Protocol):
    get_paginator: Callable[..., Any]
    head_bucket: Callable[..., Any]
    head_object: Callable[..., Any]
    get_object: Callable[..., Any]


@dataclass
class S3TreeConfig:
    """Optional global defaults retained for backwards compatibility."""

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    endpoint_url: str | None = None
    region_name: str | None = None
    profile_name: str | None = None
