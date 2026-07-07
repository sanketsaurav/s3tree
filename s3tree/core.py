"""Core S3 tree navigation API."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from json import dumps
from typing import Any, NoReturn, cast, overload
from urllib.parse import unquote, urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from . import config
from .exceptions import BucketAccessDenied, BucketNotFound, DirectoryNotFound
from .models import Directory, File, TreeEntry
from .types import S3Client, TreeDict, TreeEntryDict, TreePageDict
from .utils import normalize_path


@dataclass(frozen=True)
class S3TreePage(Sequence[TreeEntry]):
    """One bounded page of children below an S3 prefix."""

    bucket_name: str
    prefix: str
    delimiter: str
    directories: list[Directory]
    files: list[File]
    next_token: str | None = None

    @overload
    def __getitem__(self, index: int) -> TreeEntry: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[TreeEntry]: ...

    def __getitem__(self, index: int | slice) -> TreeEntry | Sequence[TreeEntry]:
        return self.entries[index]

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[TreeEntry]:
        return iter(self.entries)

    @property
    def entries(self) -> list[TreeEntry]:
        return [*self.directories, *self.files]

    @property
    def path(self) -> str:
        return self.prefix

    @property
    def has_more(self) -> bool:
        return self.next_token is not None

    @property
    def num_files(self) -> int:
        return len(self.files)

    @property
    def num_directories(self) -> int:
        return len(self.directories)

    def to_list(self) -> list[TreeEntryDict]:
        return [entry.to_dict() for entry in self]

    def to_dict(self) -> TreePageDict:
        return TreePageDict(
            bucket=self.bucket_name,
            prefix=self.prefix,
            path=self.path,
            delimiter=self.delimiter,
            num_directories=self.num_directories,
            num_files=self.num_files,
            next_token=self.next_token,
            has_more=self.has_more,
            children=self.to_list(),
        )

    @property
    def as_dict(self) -> TreePageDict:
        return self.to_dict()

    def to_json(self) -> str:
        return dumps(self.to_dict())

    @property
    def as_json(self) -> str:
        return self.to_json()


class S3Tree(Sequence[TreeEntry]):
    """Immediate children under an S3 bucket prefix.

    S3Tree uses the standard Boto3 credential chain by default. For
    S3-compatible providers such as Cloudflare R2, MinIO, Wasabi, or DigitalOcean
    Spaces, pass endpoint_url and any provider-specific region name required by
    that service.
    """

    KEY_DELIMITER = "/"

    def __init__(
        self,
        bucket_name: str,
        path: str | None = None,
        *,
        prefix: str | None = None,
        client: object | None = None,
        session: boto3.Session | None = None,
        profile_name: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        botocore_config: Config | None = None,
        verify: bool | str | None = None,
        delimiter: str = KEY_DELIMITER,
        page_size: int | None = None,
        max_items: int | None = None,
        request_payer: str | None = None,
        expected_bucket_owner: str | None = None,
        validate_bucket: bool = True,
        enrich_metadata: bool = False,
        load: bool = True,
    ) -> None:
        if path is not None and prefix is not None:
            raise ValueError("Pass either path or prefix, not both.")

        self.bucket_name = bucket_name
        self.path = normalize_path(prefix if prefix is not None else path)
        self.prefix = self.path
        self.delimiter = delimiter
        self.page_size = page_size
        self.max_items = max_items
        self.request_payer = request_payer
        self.expected_bucket_owner = expected_bucket_owner
        self.enrich_metadata = enrich_metadata
        self.endpoint_url = endpoint_url or config.endpoint_url
        self.region_name = region_name or config.region_name
        self.profile_name = profile_name or config.profile_name
        self._access_key = aws_access_key_id or config.aws_access_key_id
        self._secret_key = aws_secret_access_key or config.aws_secret_access_key
        self._session_token = aws_session_token or config.aws_session_token
        self._botocore_config = botocore_config
        self._verify = verify
        self._session = session

        self.client: S3Client = cast(S3Client, client or self._build_client())

        if validate_bucket:
            self._ensure_bucket_exists()

        self.directories: list[Directory] = []
        self.files: list[File] = []
        self._entries = self._fetch_tree() if load else []

    @classmethod
    def from_client(
        cls,
        bucket_name: str,
        client: object,
        path: str | None = None,
        **kwargs: Any,
    ) -> S3Tree:
        """Create a tree from an already configured S3-compatible client."""

        return cls(bucket_name=bucket_name, path=path, client=client, **kwargs)

    @classmethod
    def from_uri(cls, uri: str, **kwargs: Any) -> S3Tree:
        bucket_name, prefix = _parse_s3_uri(uri)
        return cls(bucket_name=bucket_name, prefix=prefix, **kwargs)

    @classmethod
    def fetch_page(
        cls,
        bucket_name: str,
        path: str | None = None,
        *,
        prefix: str | None = None,
        starting_token: str | None = None,
        page_size: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> S3TreePage:
        tree = cls(
            bucket_name=bucket_name,
            path=path,
            prefix=prefix,
            page_size=page_size,
            max_items=max_items,
            load=False,
            **kwargs,
        )
        return tree.list_page(
            starting_token=starting_token,
            page_size=page_size,
            max_items=max_items,
        )

    @classmethod
    def fetch_page_from_uri(
        cls,
        uri: str,
        *,
        starting_token: str | None = None,
        page_size: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> S3TreePage:
        bucket_name, prefix = _parse_s3_uri(uri)
        return cls.fetch_page(
            bucket_name=bucket_name,
            prefix=prefix,
            starting_token=starting_token,
            page_size=page_size,
            max_items=max_items,
            **kwargs,
        )

    @overload
    def __getitem__(self, index: int) -> TreeEntry: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[TreeEntry]: ...

    def __getitem__(self, index: int | slice) -> TreeEntry | Sequence[TreeEntry]:
        return self._entries[index]

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[TreeEntry]:
        return iter(self._entries)

    @property
    def num_files(self) -> int:
        return len(self.files)

    @property
    def num_directories(self) -> int:
        return len(self.directories)

    @property
    def is_root(self) -> bool:
        return self.prefix == ""

    @property
    def _request_options(self) -> dict[str, str]:
        options = {}
        if self.request_payer:
            options["RequestPayer"] = self.request_payer
        if self.expected_bucket_owner:
            options["ExpectedBucketOwner"] = self.expected_bucket_owner
        return options

    def walk(self, max_depth: int | None = None) -> Iterator[TreeEntry]:
        """Yield entries recursively below this tree.

        max_depth counts directory levels below this tree. A max_depth of 0
        yields only the immediate children already represented by this tree.
        """

        for entry in self:
            yield entry
            if isinstance(entry, Directory) and max_depth != 0:
                next_depth = None if max_depth is None else max_depth - 1
                yield from entry.get_tree().walk(max_depth=next_depth)

    def iter_files(self, recursive: bool = False) -> Iterator[File]:
        entries: Iterator[TreeEntry] = self.walk() if recursive else iter(self)
        for entry in entries:
            if isinstance(entry, File):
                yield entry

    def iter_directories(self, recursive: bool = False) -> Iterator[Directory]:
        entries: Iterator[TreeEntry] = self.walk() if recursive else iter(self)
        for entry in entries:
            if isinstance(entry, Directory):
                yield entry

    def list_page(
        self,
        *,
        starting_token: str | None = None,
        page_size: int | None = None,
        max_items: int | None = None,
        enrich_metadata: bool | None = None,
    ) -> S3TreePage:
        effective_page_size = page_size if page_size is not None else self.page_size
        effective_max_items = max_items if max_items is not None else self.max_items
        if effective_max_items is None:
            effective_max_items = effective_page_size or 100

        page, saw_directory_marker = self._collect_listing(
            starting_token=starting_token,
            page_size=effective_page_size,
            max_items=effective_max_items,
            enrich_metadata=self.enrich_metadata
            if enrich_metadata is None
            else enrich_metadata,
        )
        self._raise_if_missing_directory(page, saw_directory_marker)
        return page

    def to_list(self) -> list[TreeEntryDict]:
        return [entry.to_dict() for entry in self]

    def to_dict(self) -> TreeDict:
        return {
            "bucket": self.bucket_name,
            "prefix": self.prefix,
            "path": self.path,
            "delimiter": self.delimiter,
            "num_directories": self.num_directories,
            "num_files": self.num_files,
            "children": self.to_list(),
        }

    @property
    def as_dict(self) -> TreeDict:
        return self.to_dict()

    def to_json(self) -> str:
        return dumps(self.to_dict())

    @property
    def as_json(self) -> str:
        return self.to_json()

    def _build_client(self) -> S3Client:
        session = self._session or boto3.Session(
            profile_name=self.profile_name,
            region_name=self.region_name,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            aws_session_token=self._session_token,
        )
        client_kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": self.region_name,
            "endpoint_url": self.endpoint_url,
            "config": self._botocore_config,
        }
        if self._verify is not None:
            client_kwargs["verify"] = self._verify

        client = session.client(
            **{key: value for key, value in client_kwargs.items() if value is not None}
        )
        return cast(S3Client, client)

    def _fetch_tree(self) -> list[TreeEntry]:
        page, saw_directory_marker = self._collect_listing(
            page_size=self.page_size,
            max_items=self.max_items,
            enrich_metadata=self.enrich_metadata,
        )
        self._raise_if_missing_directory(page, saw_directory_marker)
        self.directories = page.directories
        self.files = page.files
        return page.entries

    def _collect_listing(
        self,
        *,
        starting_token: str | None = None,
        page_size: int | None = None,
        max_items: int | None = None,
        enrich_metadata: bool = False,
    ) -> tuple[S3TreePage, bool]:
        paginator = self.client.get_paginator("list_objects_v2")
        list_options: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Delimiter": self.delimiter,
            "Prefix": self.prefix,
            **self._request_options,
        }
        pagination_config: dict[str, int | str] = {}
        if page_size is not None:
            pagination_config["PageSize"] = page_size
        if max_items is not None:
            pagination_config["MaxItems"] = max_items
        if starting_token is not None:
            pagination_config["StartingToken"] = starting_token
        if pagination_config:
            list_options["PaginationConfig"] = pagination_config

        directories: list[Directory] = []
        files: list[File] = []
        seen_prefixes: set[str] = set()
        saw_directory_marker = False

        response: dict[str, Any]
        try:
            response = paginator.paginate(**list_options).build_full_result()
        except ClientError as exc:
            self._raise_domain_error(exc)

        for prefix in response.get("CommonPrefixes", []):
            directory = Directory.from_api(prefix, self)
            if directory.path not in seen_prefixes:
                seen_prefixes.add(directory.path)
                directories.append(directory)

        for item in response.get("Contents", []):
            key = item.get("Key")
            if key == self.prefix and key.endswith(self.delimiter):
                saw_directory_marker = True
                continue
            file_obj = File.from_api(item, self)
            if enrich_metadata:
                file_obj = file_obj.load_metadata()
            files.append(file_obj)

        return (
            S3TreePage(
                bucket_name=self.bucket_name,
                prefix=self.prefix,
                delimiter=self.delimiter,
                directories=directories,
                files=files,
                next_token=response.get("NextToken"),
            ),
            saw_directory_marker,
        )

    def _raise_if_missing_directory(
        self,
        page: S3TreePage,
        saw_directory_marker: bool,
    ) -> None:
        has_no_entries = not page.directories and not page.files
        if has_no_entries and not saw_directory_marker and not self.is_root:
            raise DirectoryNotFound(self.prefix)

    def _ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name, **self._request_options)
        except ClientError as exc:
            self._raise_domain_error(exc)

    def _raise_domain_error(self, exc: ClientError) -> NoReturn:
        code = exc.response.get("Error", {}).get("Code")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

        if code in {"NoSuchBucket", "404", "NotFound"} or status == 404:
            raise BucketNotFound(self.bucket_name) from exc
        if code in {"AccessDenied", "403"} or status == 403:
            raise BucketAccessDenied(self.bucket_name) from exc
        raise exc

    def _spawn(self, prefix: str) -> S3Tree:
        return self.__class__(
            bucket_name=self.bucket_name,
            prefix=prefix,
            client=self.client,
            delimiter=self.delimiter,
            page_size=self.page_size,
            max_items=self.max_items,
            request_payer=self.request_payer,
            expected_bucket_owner=self.expected_bucket_owner,
            enrich_metadata=self.enrich_metadata,
            validate_bucket=False,
        )


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError("S3Tree URIs must use the s3:// scheme.")
    if not parsed.netloc:
        raise ValueError("S3Tree URIs must include a bucket name.")
    if parsed.params or parsed.query or parsed.fragment or ";" in parsed.path:
        raise ValueError("S3Tree URIs must not include params, query, or fragment.")

    prefix = unquote(parsed.path.lstrip("/"))
    return parsed.netloc, prefix
