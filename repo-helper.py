#!/usr/bin/env python
#
# repo-helper: Given a Git URI, clone it into a "namespaced" subdirectory and
#   symlink it to the base subdirectory.
#
# Motivation: I want to see all my repos, while keeping things tidy.
#
# If cloning <https://github.com/jan-warchol/selenized>, the paths will be:
#   clone_base: /Users/timc/src/hosts
#   host_dir:   /Users/timc/src/hosts/github.com
#   owner_dir:  /Users/timc/src/hosts/github.com/jan-warchol
#   project:    selenized
#   symlink:    /Users/timc/src/selenized -> /Users/timc/src/hosts/github.com/jan-warchol/selenized
#
# Caveat 1: If there are two repositories with the same name at different
#   paths, the symlinking will fail. The workaround will be to prepend the
#   second repository's symlink name with the project, then a dunder, then the
#   repository name.
# Example: johnny/dotfiles already exists, and suzy/dotfiles is added. Instead
#   of a symlink to ~/src/dotfiles, I'll create ~/src/suzy__dotfiles.

# TODO: Add create functions.
# TODO: Add delete functionality.

import git
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# I'm not adding any parameter guards yet.
url = sys.argv[1]

# symlink_base is not configurable yet.
symlink_base = "/Users/timc/src"
clone_base = os.path.join(symlink_base, "hosts")

# Parse both HTTPS and SSH URL formats:
#   HTTPS: https://github.com/timcondit/repo-helper.git
#   SSH:   git@github.com:timcondit/repo-helper.git
ssh_match = re.match(r"^git@([^:]+):(.+)$", url)
if ssh_match:
    netloc = ssh_match.group(1)
    repo_path = ssh_match.group(2)
else:
    o = urlparse(url)
    netloc = o.netloc
    repo_path = o.path.lstrip("/")

host_dir = os.path.join(clone_base, netloc)
Path(host_dir).mkdir(parents=True, exist_ok=True)

owner, project_raw = repo_path.rsplit("/", 1)
project = project_raw.removesuffix(".git")
owner_dir = os.path.join(host_dir, owner)
Path(owner_dir).mkdir(parents=True, exist_ok=True)

# There's no explicit auth yet. You'll need to provide a GitLab or GitHub
# personal access token, at least the first time. git-python may be caching
# credentials.
try:
    # I'm not adding any filesystem guards yet.
    clone_url = url if url.endswith(".git") else url + ".git"
    print(f"Cloning {clone_url} ~> {os.path.join(owner_dir, project)}")
    git.Git(owner_dir).clone(clone_url)

except git.exc.GitCommandError as e:
    print(f"\n{e}")
    print("\nWill still attempt to create symlink if needed.")

src = os.path.join(owner_dir, project)
dst = os.path.join(symlink_base, project)
# I'm not adding any is_symlink() guards yet.
try:
    Path(dst).symlink_to(Path(src))
except Exception as e:
    print(f"\n{e}")
