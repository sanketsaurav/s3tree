"""Typed tree navigation for S3 and S3-compatible object storage."""

from __future__ import annotations

from .__version__ import __version__
from .models import Directory, File, S3Object, TreeEntry
from .types import S3TreeConfig

config = S3TreeConfig()
VERSION = __version__

from .core import S3Tree, S3TreePage  # noqa

__all__ = [
    "Directory",
    "File",
    "S3Object",
    "S3Tree",
    "S3TreePage",
    "TreeEntry",
    "VERSION",
    "__version__",
    "config",
]
