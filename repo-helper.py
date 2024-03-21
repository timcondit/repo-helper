#!/usr/bin/env python
#
# repo-helper: Given a Git URI, clone it into a "namespaced" subdirectory and symlink it to the base subdirectory.
#
# Motivation:   I want to see all my repos, while keeping things tidy.
# Caveat:       If there are two repositories with the same name at different paths, the symlinking will fail. The workaround will be to prepend the second repository's symlink name with the project, then a dunder, then the repository name.
#   Example: johnny/dotfiles already exists, and suzy/dotfiles is added. Instead of a symlink to ~/src/dotfiles, I'll create ~/src/suzy__dotfiles.

from pathlib import Path
from urllib.parse import urlparse
import git
import os
import sys

url = sys.argv[1]
o = urlparse(url)
# print(f"o.scheme: {o.scheme}")
# print(f"o.netloc: {o.netloc}")
# print(f"o.path: {o.path}")

# Create netloc directory if it doesn't exist.
path1 = "/Users/tcondit/src"
path2 = os.path.join(path1, o.netloc)
Path(path2).mkdir(parents=True, exist_ok=True)

# Create path3 minus the project name if it doesn't exist.
path3, project = o.path.rsplit("/", 1)
path3 = path3.lstrip("/")
path4 = os.path.join(path2, path3)

# print(f"path1: {path1}")
# print(f"path2: {path2}")
# print(f"path3: {path3}")
# print(f"path4: {path4}")
# print(f"project: {project}")

# This '.lstrip("/")' is sure to cause problems.
# Path(os.path.join(path2, path3.lstrip("/"))).mkdir(parents=True, exist_ok=True)
Path(path4).mkdir(parents=True, exist_ok=True)

# There's no explicit auth yet. You'll need to provide a GitLab personal access token.

try:
    print(f"Cloning {url} ~> {path4}")
    git.Git(path4).clone(url)
except git.exc.GitCommandError as e:
    print(f"\n{e}")

