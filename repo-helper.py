#!/usr/bin/env python
#
# repo-helper: Given a Git URI, clone it into a "namespaced" subdirectory and
#   symlink it to the base subdirectory.
#
# Motivation: I want to see all my repos, while keeping things tidy.
#
# If cloning <https://github.com/jan-warchol/selenized>, the paths will be:
#   path1: /Users/tcondit/src
#   path2: /Users/tcondit/src/github.com
#   path3: jan-warchol
#   path4: /Users/tcondit/src/github.com/jan-warchol
#   project: selenized
#
# Caveat 1: If there are two repositories with the same name at different
#   paths, the symlinking will fail. The workaround will be to prepend the
#   second repository's symlink name with the project, then a dunder, then the
#   repository name.
# Example: johnny/dotfiles already exists, and suzy/dotfiles is added. Instead
#   of a symlink to ~/src/dotfiles, I'll create ~/src/suzy__dotfiles.

import git
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# I'm not adding any parameter guards yet.
url = sys.argv[1]
o = urlparse(url)

# path1 is not configurable yet.
path1 = "/Users/tcondit/src"
path2 = os.path.join(path1, o.netloc)
Path(path2).mkdir(parents=True, exist_ok=True)

path3, project = o.path.rsplit("/", 1)
# This '.lstrip("/")' may cause problems.
path4 = os.path.join(path2, path3.lstrip("/"))
Path(path4).mkdir(parents=True, exist_ok=True)

# There's no explicit auth yet. You'll need to provide a GitLab or GitHub
# personal access token, at least the first time. git-python may be caching
# credentials.
try:
    # I'm not adding any filesystem guards yet.
    print(f"Cloning {url} ~> {path4}")
    git.Git(path4).clone(url.strip(".git"))
except git.exc.GitCommandError as e:
    print(f"\n{e}")
    print("\nWill still attempt to create symlink if needed.")

src = os.path.join(path4, project)
dst = os.path.join(path1, project)
# I'm not adding any is_symlink() guards yet.
try:
    Path(dst).symlink_to(Path(src))
except Exception as e:
    print(f"\n{e}")
