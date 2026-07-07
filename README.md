# S3Tree

Typed tree navigation for S3 and S3-compatible object storage.

S3Tree gives Python applications a small, predictable object model for browsing
S3 prefixes as directories and files. It is designed for admin dashboards, data
explorers, asset browsers, migration tooling, and APIs that need clean JSON
without adopting a full filesystem abstraction.

S3 is still object storage, not a real filesystem. S3Tree focuses on the common
application-level need: "show me the immediate children under this prefix, let
me traverse deeper, and give me typed metadata I can serialize."

## Installation

```bash
pip install s3tree
```

## Basic Usage

```python
import s3tree

tree = s3tree.S3Tree(bucket_name="my-bucket", prefix="datasets/2026")

for entry in tree:
    print(entry.kind, entry.name, entry.path)

print(tree.num_directories)
print(tree.num_files)
```

S3Tree uses Boto3's standard credential chain by default, including environment
variables, profiles, IAM roles, web identity credentials, IAM Identity Center,
container credentials, and EC2 instance metadata.

## Traverse Directories

```python
tree = s3tree.S3Tree("my-bucket", prefix="assets")

for directory in tree.directories:
    child_tree = directory.get_tree()
    print(directory.name, len(child_tree))
```

Recursive traversal is available when you ask for it:

```python
for entry in tree.walk(max_depth=2):
    print(entry.kind, entry.path)
```

## Read Files

```python
file = tree.files[0]

data = file.read_bytes()
text = file.read_text()
```

The old `file.read()` method is still available as a UTF-8 text alias, but new
code should prefer `read_bytes()` or `read_text()`.

For large objects, stream bytes instead of loading the full object into memory:

```python
for chunk in file.iter_chunks(chunk_size=8 * 1024 * 1024):
    process(chunk)
```

Use `open()` when you need direct access to Boto3's streaming body:

```python
body = file.open()
try:
    first_kb = body.read(1024)
finally:
    body.close()
```

## Cursor-Based Pages

Use `fetch_page()` when you are building a UI, API, or background worker that
should not materialize a whole prefix at once.

```python
page = s3tree.S3Tree.fetch_page(
    "my-bucket",
    prefix="datasets",
    page_size=100,
)

for entry in page:
    print(entry.kind, entry.path)

next_token = page.next_token
```

Pass `starting_token=next_token` to fetch the next page. Tokens are Boto3
paginator tokens and should be treated as opaque strings.

## URI Helpers

```python
tree = s3tree.S3Tree.from_uri("s3://my-bucket/datasets/2026")
page = s3tree.S3Tree.fetch_page_from_uri("s3://my-bucket/datasets/2026")
```

The URI target is interpreted as a tree prefix. Query strings, fragments, and
raw path params are rejected so user-facing `s3://` input cannot silently change
the listing request.

## Metadata Enrichment

`ListObjectsV2` returns enough data for browsing, but not all object metadata.
Call `load_metadata()` for one file, or pass `enrich_metadata=True` to load
metadata for every file in the listed tree/page.

```python
file = tree.files[0].load_metadata()
print(file.content_type)
print(file.metadata)
print(file.version_id)
```

`enrich_metadata=True` issues one `HeadObject` request per file, so keep it off
for large directory listings unless your UI needs that data immediately.

## JSON for Applications

```python
payload = tree.to_dict()
json_payload = tree.to_json()
```

The tree payload includes the bucket, prefix, delimiter, counts, and serialized
children. Each child has a `kind` field:

```json
{
  "bucket": "my-bucket",
  "prefix": "datasets/2026/",
  "delimiter": "/",
  "num_directories": 1,
  "num_files": 2,
  "children": [
    {
      "kind": "directory",
      "name": "images",
      "path": "datasets/2026/images/",
      "prefix": "datasets/2026/images/"
    }
  ]
}
```

## S3-Compatible Providers

Pass `endpoint_url` and any provider-specific region value to use object storage
services that implement the S3 API. S3Tree only depends on the standard
`HeadBucket`, `ListObjectsV2`, `HeadObject`, and `GetObject` calls.

Cloudflare R2:

```python
tree = s3tree.S3Tree(
    "my-bucket",
    prefix="datasets",
    endpoint_url="https://<ACCOUNT_ID>.r2.cloudflarestorage.com",
    region_name="auto",
    aws_access_key_id="<ACCESS_KEY_ID>",
    aws_secret_access_key="<SECRET_ACCESS_KEY>",
)
```

MinIO or another custom endpoint:

```python
tree = s3tree.S3Tree(
    "my-bucket",
    endpoint_url="http://localhost:9000",
    region_name="us-east-1",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
)
```

Providers such as Wasabi, DigitalOcean Spaces, and Backblaze B2 work the same
way: configure the provider endpoint and credentials, then use the normal tree
API.

If your application already owns a configured client, inject it directly:

```python
import boto3

client = boto3.client(
    "s3",
    endpoint_url="https://<ACCOUNT_ID>.r2.cloudflarestorage.com",
    region_name="auto",
)

tree = s3tree.S3Tree.from_client("my-bucket", client, prefix="datasets")
```

For path-style endpoints, pass a Botocore config:

```python
from botocore.config import Config

tree = s3tree.S3Tree(
    "my-bucket",
    endpoint_url="http://localhost:9000",
    region_name="us-east-1",
    botocore_config=Config(s3={"addressing_style": "path"}),
)
```

For S3 Express directory buckets, access points, Outposts, custom signers, or
provider-specific endpoint rules, create the exact Boto3 client required by that
provider and pass it with `S3Tree.from_client()` or `S3Tree.fetch_page(...,
client=client)`. S3Tree deliberately does not rewrite advanced bucket names,
ARNs, or zonal endpoints itself.

## API Notes

- Listings use Boto3's `list_objects_v2` paginator.
- `prefix` and the legacy `path` argument both refer to the tree root prefix.
- Prefixes are normalized so `assets`, `/assets`, and `assets/` all target
  `assets/`.
- `from_uri()` accepts `s3://bucket/prefix` and decodes URL-escaped path
  segments before prefix normalization.
- Construction validates the bucket with `head_bucket` by default. Pass
  `validate_bucket=False` to skip that extra request.
- For requester-pays buckets, pass `request_payer="requester"`.
- To enforce an expected AWS account owner, pass `expected_bucket_owner`.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ty check --python "$(python -c 'import sys; print(sys.executable)')"
pytest
python -m build
```
