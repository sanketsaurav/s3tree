#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['S3Tree', 'config', 'VERSION']

from .types import S3TreeConfig
from .__version__ import __version__

config = S3TreeConfig()
VERSION = __version__

from .core import S3Tree  # noqa
