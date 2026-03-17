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
# Note: If two repositories share the same project name (e.g.,
#   johnny/dotfiles and suzy/dotfiles), only the first gets a symlink.
#   The second clone still succeeds but the symlink is skipped with a
#   warning. The repo is accessible via its full path under hosts/.

import argparse
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

    Skips if the destination directory already exists. There's no explicit
    auth yet. You'll need to provide a GitLab or GitHub personal access
    token, at least the first time. git-python may be caching credentials.
    """
    dest = os.path.join(owner_dir, project)
    if os.path.isdir(dest):
        print(f"Already cloned: {dest}")
        return

    clone_url = url if url.endswith(".git") else url + ".git"
    print(f"Cloning {clone_url} ~> {dest}")
    git.Git(owner_dir).clone(clone_url)


def create_symlink(owner_dir, project):
    """Create a symlink from SYMLINK_BASE/<project> to owner_dir/<project>.

    If a symlink with the same name already exists (e.g., another repo with
    the same project name), prints a warning and skips. The repo is still
    accessible via its full path under CLONE_BASE.
    """
    src = os.path.join(owner_dir, project)
    dst = os.path.join(SYMLINK_BASE, project)
    dst_path = Path(dst)
    if dst_path.is_symlink() or dst_path.exists():
        existing_target = os.readlink(dst) if dst_path.is_symlink() else dst
        if os.path.realpath(existing_target) == os.path.realpath(src):
            print(f"Symlink already exists: {dst} -> {src}")
        else:
            print(f"Warning: symlink {dst} already exists -> {existing_target}")
            print(f"  Skipping symlink for {src}")
            print(f"  Access this repo at its full path: {src}")
        return
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


def validate_remotes():
    """Verify that all repos under CLONE_BASE have correct origin remotes.

    For each git repo found, the expected remote is derived from its path:
        ~/src/hosts/<host>/<owner>/<project>
    should have an origin of either:
        https://<host>/<owner>/<project>.git   (HTTPS)
        git@<host>:<owner>/<project>.git       (SSH)

    Forks are recognized when origin doesn't match the path but an
    upstream remote does (i.e., origin points to the user's fork and
    upstream points to the original repo).
    """
    clone_base = Path(CLONE_BASE)
    if not clone_base.is_dir():
        print(f"Clone base {CLONE_BASE} does not exist.")
        return

    errors = 0
    checked = 0
    for git_dir in sorted(clone_base.rglob(".git")):
        if not git_dir.is_dir():
            continue

        repo_dir = git_dir.parent
        # Derive host/owner/project from path relative to CLONE_BASE
        rel = repo_dir.relative_to(clone_base)
        parts = rel.parts
        if len(parts) != 3:
            print(f"SKIP     {repo_dir} (unexpected depth: {'/'.join(parts)})")
            continue

        host, owner, project = parts
        expected_https = f"https://{host}/{owner}/{project}.git"
        expected_ssh = f"git@{host}:{owner}/{project}.git"
        expected = (expected_https, expected_ssh)

        try:
            repo = git.Repo(repo_dir)
            origin_url = repo.remotes.origin.url
        except Exception as e:
            print(f"ERROR    {repo_dir}: {e}")
            errors += 1
            continue

        checked += 1
        if origin_url in expected:
            print(f"OK       {repo_dir}")
        else:
            # Check if this is a fork: origin is the user's fork,
            # upstream points to the original repo
            upstream_url = None
            if "upstream" in [r.name for r in repo.remotes]:
                upstream_url = repo.remotes.upstream.url

            if upstream_url in expected:
                print(f"FORK     {repo_dir}")
                print(f"  origin:   {origin_url}")
                print(f"  upstream: {upstream_url}")
            else:
                print(f"MISMATCH {repo_dir}")
                print(f"  origin:   {origin_url}")
                if upstream_url:
                    print(f"  upstream: {upstream_url}")
                print(f"  expected: {expected_https}")
                print(f"       or:  {expected_ssh}")
                errors += 1

    print(f"\nChecked {checked} repo(s), {errors} issue(s) found.")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="repo-helper",
        description=(
            "Clone git repos into namespaced subdirectories under "
            f"{CLONE_BASE}/ and symlink them to {SYMLINK_BASE}/."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    # clone (default when just a URL is given)
    clone_parser = subparsers.add_parser(
        "clone",
        help="Clone a repo and create a symlink to it.",
        description=(
            "Clone a git repo into ~/src/hosts/<host>/<owner>/<project> "
            "and create a symlink at ~/src/<project>. Both HTTPS and SSH "
            "URLs are supported. The .git suffix is added to the clone URL "
            "if not already present, so the remote matches GitHub's format."
        ),
    )
    clone_parser.add_argument(
        "url",
        help=(
            "Git URL to clone. Accepts HTTPS (https://github.com/owner/repo) "
            "or SSH (git@github.com:owner/repo.git). The .git suffix is added "
            "automatically if not present."
        ),
    )

    # delete
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a cloned repo and its symlink.",
        description=(
            "Remove the cloned repo and its symlink. Also cleans up empty "
            "parent directories (owner, host) under the clone base."
        ),
    )
    delete_parser.add_argument(
        "url",
        help=(
            "Git URL of the repo to delete. Accepts the same HTTPS or SSH "
            "formats used for cloning. The host, owner, and project are "
            "derived from the URL to locate the repo and symlink."
        ),
    )

    # validate
    subparsers.add_parser(
        "validate",
        help="Verify that all repo remotes are correct.",
        description=(
            "Walk all repos under ~/src/hosts/ and check that each repo's "
            "origin remote matches the expected URL derived from its "
            "directory path.\n\n"
            "For forked repos, origin typically points to your fork rather "
            "than the upstream project. To avoid false positives, add an "
            "upstream remote pointing to the original repo:\n\n"
            "  git remote add upstream https://github.com/<owner>/<project>.git\n\n"
            "When an upstream remote is present and matches the expected "
            "URL, the repo is reported as FORK instead of MISMATCH."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    return parser


def main():
    parser = build_parser()

    # Support bare URL as shorthand for "clone <url>" and
    # legacy --delete/--validate flags
    subcommands = {"clone", "delete", "validate"}
    args = sys.argv[1:]
    if args and args[0] == "--delete":
        args = ["delete"] + args[1:]
    elif args and args[0] == "--validate":
        args = ["validate"] + args[1:]
    elif args and args[0] not in subcommands and not args[0].startswith("-"):
        # Bare URL → treat as clone (must look like a URL)
        if "://" in args[0] or args[0].startswith("git@"):
            args = ["clone"] + args

    parsed = parser.parse_args(args)

    if parsed.command == "clone":
        host, owner, project = parse_url(parsed.url)
        owner_dir = os.path.join(CLONE_BASE, host, owner)
        Path(owner_dir).mkdir(parents=True, exist_ok=True)

        try:
            clone_repo(parsed.url, owner_dir, project)
        except git.exc.GitCommandError as e:
            print(f"\n{e}")
            print("\nWill still attempt to create symlink if needed.")

        try:
            create_symlink(owner_dir, project)
        except Exception as e:
            print(f"\n{e}")

    elif parsed.command == "delete":
        host, owner, project = parse_url(parsed.url)
        owner_dir = os.path.join(CLONE_BASE, host, owner)
        delete_repo(owner_dir, project)

    elif parsed.command == "validate":
        validate_remotes()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
