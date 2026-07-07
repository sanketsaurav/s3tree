"""Model objects used to represent S3 prefixes and objects."""

from __future__ import annotations

import mimetypes
import os
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import datetime
from json import dumps
from typing import TYPE_CHECKING, Any, Literal, cast

from botocore.exceptions import ClientError

from .exceptions import FileNotFound
from .types import BodyStream, DirectoryDict, FileDict
from .utils import humanize_file_size

if TYPE_CHECKING:
    from .core import S3Tree


def _file_type(content_type: str | None) -> str:
    if content_type is None:
        return "binary"

    category = content_type.split("/", 1)[0]
    if category in {"image", "text"}:
        return category
    if category in {"audio", "video"}:
        return "media"
    return "binary"


def _is_missing_key_error(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code")
    return code in {"NoSuchKey", "404", "NotFound"}


@dataclass(frozen=True)
class Directory:
    """A common prefix that behaves like a directory in an S3 tree."""

    path: str
    s3tree: S3Tree = field(repr=False, compare=False)
    kind: Literal["directory"] = "directory"

    @classmethod
    def from_api(cls, data: dict[str, Any], s3tree: S3Tree) -> Directory:
        return cls(path=data["Prefix"], s3tree=s3tree)

    @property
    def prefix(self) -> str:
        return self.path

    @property
    def name(self) -> str:
        return os.path.basename(self.path.rstrip(self.s3tree.delimiter))

    @property
    def bucket_name(self) -> str:
        return self.s3tree.bucket_name

    def get_tree(self) -> S3Tree:
        return self.s3tree._spawn(self.path)

    def to_dict(self) -> DirectoryDict:
        return DirectoryDict(
            kind=self.kind,
            name=self.name,
            path=self.path,
            prefix=self.prefix,
        )

    @property
    def as_dict(self) -> DirectoryDict:
        return self.to_dict()

    def to_json(self) -> str:
        return dumps(self.to_dict())

    @property
    def as_json(self) -> str:
        return self.to_json()

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class File:
    """An S3 object returned by a tree listing."""

    path: str
    s3tree: S3Tree = field(repr=False, compare=False)
    etag: str | None = None
    last_modified: datetime | None = None
    size_in_bytes: int = 0
    storage_class: str | None = None
    content_type_hint: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    version_id: str | None = None
    checksum_algorithm: tuple[str, ...] = ()
    checksum_type: str | None = None
    restore_status: dict[str, Any] | None = None
    kind: Literal["file"] = "file"

    @classmethod
    def from_api(cls, data: dict[str, Any], s3tree: S3Tree) -> File:
        return cls(
            path=data["Key"],
            s3tree=s3tree,
            etag=data.get("ETag"),
            last_modified=data.get("LastModified"),
            size_in_bytes=data.get("Size", 0),
            storage_class=data.get("StorageClass"),
            checksum_algorithm=tuple(data.get("ChecksumAlgorithm", ())),
            checksum_type=data.get("ChecksumType"),
            restore_status=data.get("RestoreStatus"),
        )

    @property
    def key(self) -> str:
        return self.path

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def size(self) -> str:
        return humanize_file_size(self.size_in_bytes)

    @property
    def content_type(self) -> str | None:
        if self.content_type_hint:
            return self.content_type_hint
        content_type, _ = mimetypes.guess_type(self.path)
        return content_type

    @property
    def file_type(self) -> str:
        return _file_type(self.content_type)

    def _get_object_response(self) -> dict[str, Any]:
        try:
            return self.s3tree.client.get_object(
                Bucket=self.s3tree.bucket_name,
                Key=self.path,
                **self.s3tree._request_options,
            )
        except ClientError as exc:
            if _is_missing_key_error(exc):
                raise FileNotFound(self.path) from exc
            raise

    def open(self) -> BodyStream:
        response = self._get_object_response()
        return cast(BodyStream, response["Body"])

    def iter_chunks(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")

        body = self.open()
        try:
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            body.close()

    def read_bytes(self) -> bytes:
        response = self._get_object_response()
        body = cast(BodyStream, response["Body"])
        try:
            return body.read()
        finally:
            body.close()

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.read_bytes().decode(encoding)

    def read(self) -> str:
        """Read the object as UTF-8 text.

        This method is retained for backwards compatibility. New code should
        prefer read_text() or read_bytes() so binary behavior is explicit.
        """

        return self.read_text()

    def load_metadata(self) -> File:
        try:
            response = self.s3tree.client.head_object(
                Bucket=self.s3tree.bucket_name,
                Key=self.path,
                **self.s3tree._request_options,
            )
        except ClientError as exc:
            if _is_missing_key_error(exc):
                raise FileNotFound(self.path) from exc
            raise

        return self.with_metadata(response)

    def with_metadata(self, data: dict[str, Any]) -> File:
        return replace(
            self,
            etag=data.get("ETag", self.etag),
            last_modified=data.get("LastModified", self.last_modified),
            content_type_hint=data.get("ContentType", self.content_type_hint),
            metadata=dict(data.get("Metadata", self.metadata)),
            version_id=data.get("VersionId", self.version_id),
            size_in_bytes=data.get("ContentLength", self.size_in_bytes),
            storage_class=data.get("StorageClass", self.storage_class),
            checksum_algorithm=tuple(
                data.get("ChecksumAlgorithm", self.checksum_algorithm)
            ),
            checksum_type=data.get("ChecksumType", self.checksum_type),
            restore_status=data.get("RestoreStatus", self.restore_status),
        )

    def to_dict(self) -> FileDict:
        return FileDict(
            kind=self.kind,
            name=self.name,
            path=self.path,
            key=self.key,
            etag=self.etag,
            last_modified=(
                self.last_modified.isoformat() if self.last_modified else None
            ),
            size=self.size,
            size_in_bytes=self.size_in_bytes,
            storage_class=self.storage_class,
            content_type=self.content_type,
            file_type=self.file_type,
            metadata=self.metadata,
            version_id=self.version_id,
            checksum_algorithm=list(self.checksum_algorithm),
            checksum_type=self.checksum_type,
            restore_status=self.restore_status,
        )

    @property
    def as_dict(self) -> FileDict:
        return self.to_dict()

    def to_json(self) -> str:
        return dumps(self.to_dict())

    @property
    def as_json(self) -> str:
        return self.to_json()

    def __str__(self) -> str:
        return self.name


S3Object = File
TreeEntry = Directory | File
