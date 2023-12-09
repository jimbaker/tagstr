# Dockerfiles
This directory contains Dockerfiles for CPython of tag string v2 branch.

The dockerfile were generated with [a patched version of the official dockerfile code generator](https://github.com/koxudaxi/docker-python/blob/support_tag_string_v2_branch/apply-templates.sh).
The patched code generator and Dockerfiles exist in [Koudai's(@koxudaxi) repository](https://github.com/koxudaxi/docker-python/tree/support_tag_string_v2_branch) is fork on the official Python Dockerfile repository.

## How to build
```shell
$ docker build slim-bookworm -t tag-string-v2:slim-bookworm
```

## How to run
```shell
$ docker run -it --rm tag-string-v2:slim-bookworm 
Python 3.12.0a7+ (heads/tag-strings-v2:e37d679, Dec  9 2023, 17:58:20) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> def html(content):
...     return f"<html>{content}</html>"
...
>>> html"Hello, world!"
'<html>Hello, world!</html>'
```
