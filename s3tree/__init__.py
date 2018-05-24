#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['S3Tree', 'config']

from .types import S3TreeConfig

config = S3TreeConfig()

from .core import S3Tree  # noqa
