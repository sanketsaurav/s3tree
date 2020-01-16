# S3Tree 🌲

[![DeepSource](https://static.deepsource.io/deepsource-badge-light-mini.svg)](https://deepsource.io/gh/sanketsaurav/s3tree/?ref=repository-badge)
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


## Documentation

### Using AWS credentials

The `s3tree` module exposes a `config` object that can be used to set the AWS credentials you want to use
globally. You should ideally do this before you make any instances of `S3Tree`.

```python
>>> import s3tree
>>> s3tree.config.aws_access_key_id = '<AWS-ACCESS-KEY>'
>>> s3tree.config.aws_secret_access_key = '<AWS-SECRET-KEY>'
```

Credentials can also be passed while creating an `S3Tree` instance:

```python
>>> tree = s3tree.S3Tree('dummy-bucket', aws_access_key_id='<AWS-ACCESS-KEY>', aws_secret_access_key='<AWS-SECRET-KEY>')
```
Passing the credentials during instance creation overrides the global config.

### Fetching a tree

The `S3Tree` object represents a tree at any given path. The path can be specified while creating a new tree.
If no path, or `/` is passed, the root if the bucket is fetched.

```python
>>> tree = s3tree.S3Tree(bucket_name='dummy')  # tree at the root of the bucket `dummy`
>>> tree = s3tree.S3Tree(bucket_name='dummy', path='/admin/css')  # tree under the path `/admin/css`
>>> tree = s3tree.S3Tree(bucket_name='dummy', path='admin/css')  # this works too.
```
The `tree` object above is an iterable that contains all files and directories in this tree. `len(tree)` gives you the total size of this tree.
If you want to access files and directories separately:

```python
>>> tree.directories  # iterable for all the directories in the tree
>>> tree.files  # iterable for all the files in the tree
```

The S3Tree object can be easily represented as JSON:

```python
>>> tree.as_json
```

### The Directory object
Each element in `tree.directories` is a `Directory` object. This has attributes that help you
display the directory in a human-friendly manner, and methods to fetch the tree under itself.

```python
>>> mydir = tree.directories[0]
>>> mydir.name  # the name of this directory
css
>>> mydir.path  # the full path of this directory
/admin/css
>>> child_tree = mydir.get_tree()  # retrieve and store the tree under `mydir` to `child_tree`
>>> json_data = mydir.as_json  # JSON representation of this directory
```

### The File object
Each element in `tree.files` is a `File` object, which has attributes and methods to display properties
and read the file.

```python
>>> myfile = tree.files[0]
>>> myfile.name  # name of this file
index.js
>>> myfile.size  # human-readable size of this file
4 KB
>>> contents = myfile.read()  # reads the file and stores its contents in `contents`
>>> json_data = myfile.as_json  # JSON representation of this file obj
```
