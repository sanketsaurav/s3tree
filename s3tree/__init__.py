#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["S3Tree", "config", "VERSION"]

from .__version__ import __version__
from .types import S3TreeConfig

config = S3TreeConfig()
VERSION = __version__

from .core import S3Tree  # noqa
