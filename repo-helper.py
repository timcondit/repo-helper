#!/usr/bin/env python
#
# git-clone-and-link

from pathlib import Path
from urllib.parse import urlparse
import os
import sys

url = sys.argv[1]
o = urlparse(url)
print(f"o.scheme: {o.scheme}")
print(f"o.netloc: {o.netloc}")
print(f"o.path: {o.path}")

# Create netloc directory if it doesn't exist.
path1 = "/Users/tcondit/src"
path2 = os.path.join(path1, o.netloc)
Path(path2).mkdir(parents=True, exist_ok=True)

# Create path3 minus the project name if it doesn't exist.
path3, project = o.path.rsplit("/", 1)
print(f"path1: {path1}, path2: {path2}, path3: {path3}, project: {project}")

# This '.lstrip("/")' is sure to cause problems.
# Path(os.path.join(path2, path3.lstrip("/"))).mkdir(parents=True, exist_ok=True)
Path(os.path.join(path2, path3.lstrip("/"))).mkdir(parents=True, exist_ok=True)

# There's no explicit auth yet.


