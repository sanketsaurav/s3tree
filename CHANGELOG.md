# Changelog

## 0.4.0 (unreleased)

- Drop Python 2 support and modernize packaging around `pyproject.toml`.
- Use Boto3's standard credential chain by default instead of requiring static
  access keys.
- Add typed `Directory`, `File`, and `S3Tree` APIs with `to_dict()` and
  `to_json()` helpers.
- Add `S3Tree.fetch_page()` and `S3TreePage` for bounded cursor-based listing
  workflows.
- Add `S3Tree.from_uri()` and `S3Tree.fetch_page_from_uri()` helpers for
  `s3://bucket/prefix` inputs.
- Add `endpoint_url`, `region_name`, and client injection support for
  S3-compatible object storage such as Cloudflare R2 and MinIO.
- Document provider compatibility patterns for R2, MinIO, Wasabi, DigitalOcean
  Spaces, Backblaze B2, path-style endpoints, S3 Express directory buckets, and
  access points.
- Use the `list_objects_v2` paginator so listings are not limited to one page.
- Add optional `HeadObject` metadata enrichment with content type, user
  metadata, version IDs, checksums, and restore status.
- Add binary-safe `File.read_bytes()` and explicit text reads with
  `File.read_text()`.
- Add `File.open()` and `File.iter_chunks()` for streaming object reads.
- Replace Travis CI with GitHub Actions and update tests for current `moto`.
- Enforce 100% branch coverage and type checking with `ty` plus Ruff annotation
  rules.

## 0.3.0 (2018-06-17)
 - Add `file_type` attribute on the `File` object, with the following
 recognized possible values: `image`, `text`, `media`, and `binary`
