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

import git
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

# symlink_base is not configurable yet.
SYMLINK_BASE = "/Users/timc/src"
CLONE_BASE = os.path.join(SYMLINK_BASE, "hosts")


def parse_url(url):
    """Parse a git URL (HTTPS or SSH) and return (host, owner, project).

    Supports:
        HTTPS: https://github.com/timcondit/repo-helper.git
        SSH:   git@github.com:timcondit/repo-helper.git
    """
    ssh_match = re.match(r"^git@([^:]+):(.+)$", url)
    if ssh_match:
        host = ssh_match.group(1)
        repo_path = ssh_match.group(2)
    else:
        o = urlparse(url)
        host = o.netloc
        repo_path = o.path.lstrip("/")

    owner, project_raw = repo_path.rsplit("/", 1)
    project = project_raw.removesuffix(".git")
    return host, owner, project


def clone_repo(url, owner_dir, project):
    """Clone a git repo into owner_dir. Ensures the clone URL ends with .git.

    There's no explicit auth yet. You'll need to provide a GitLab or GitHub
    personal access token, at least the first time. git-python may be caching
    credentials.
    """
    clone_url = url if url.endswith(".git") else url + ".git"
    print(f"Cloning {clone_url} ~> {os.path.join(owner_dir, project)}")
    git.Git(owner_dir).clone(clone_url)


def create_symlink(owner_dir, project):
    """Create a symlink from SYMLINK_BASE/<project> to owner_dir/<project>."""
    src = os.path.join(owner_dir, project)
    dst = os.path.join(SYMLINK_BASE, project)
    Path(dst).symlink_to(Path(src))


def delete_repo(owner_dir, project):
    """Delete a cloned repo and its symlink.

    Removes the symlink at SYMLINK_BASE/<project> and the cloned repo at
    owner_dir/<project>. Cleans up empty parent directories (owner_dir,
    host_dir) under CLONE_BASE if they become empty after deletion.
    """
    symlink_path = Path(os.path.join(SYMLINK_BASE, project))
    repo_path = Path(os.path.join(owner_dir, project))

    # Remove symlink
    if symlink_path.is_symlink():
        symlink_path.unlink()
        print(f"Removed symlink {symlink_path}")
    else:
        print(f"No symlink found at {symlink_path}")

    # Remove cloned repo
    if repo_path.is_dir():
        shutil.rmtree(repo_path)
        print(f"Removed repo {repo_path}")
    else:
        print(f"No repo found at {repo_path}")

    # Clean up empty parent directories up to CLONE_BASE
    for parent in [Path(owner_dir), Path(owner_dir).parent]:
        if parent == Path(CLONE_BASE):
            break
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            print(f"Removed empty directory {parent}")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--delete":
        url = sys.argv[2]
        host, owner, project = parse_url(url)
        owner_dir = os.path.join(CLONE_BASE, host, owner)
        delete_repo(owner_dir, project)
    elif len(sys.argv) >= 2:
        url = sys.argv[1]
        host, owner, project = parse_url(url)

        owner_dir = os.path.join(CLONE_BASE, host, owner)
        Path(owner_dir).mkdir(parents=True, exist_ok=True)

        try:
            clone_repo(url, owner_dir, project)
        except git.exc.GitCommandError as e:
            print(f"\n{e}")
            print("\nWill still attempt to create symlink if needed.")

        try:
            create_symlink(owner_dir, project)
        except Exception as e:
            print(f"\n{e}")
    else:
        print("Usage: repo-helper.py [--delete] <url>")
        sys.exit(1)


if __name__ == "__main__":
    main()
