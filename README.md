# S3Tree 🌲

[![Build Status](https://travis-ci.org/sanketsaurav/s3tree.svg?branch=master)](https://travis-ci.org/sanketsaurav/s3tree) [![Coverage Status](https://coveralls.io/repos/github/sanketsaurav/s3tree/badge.svg?branch=master)](https://coveralls.io/github/sanketsaurav/s3tree?branch=master)

S3Tree allows you to access files stored on Amazon AWS S3 as a simple directory tree. You can traverse the tree and read files as easily as
you `os.walk`.

```python
>>> import s3tree
>>> s3tree.config.aws_access_key_id = '<AWS-ACCESS-KEY>'
>>> s3tree.config.aws_secret_access_key = '<AWS-SECRET-KEY>'
>>> tree = s3tree.S3Tree(bucket_name='my-awesome-bucket')
>>> len(tree)
77
>>> tree.num_directories
33
>>> tree.num_files
44
>>> for obj in tree: print(obj.name)
...
admin
assets
...   
index.js
```

## Installation

To install S3Tree, use pipenv (or pip):

```
$ pipenv install s3tree
```
