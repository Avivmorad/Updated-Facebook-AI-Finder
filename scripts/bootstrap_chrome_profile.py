#!/usr/bin/env python3
"""Bootstrap a dedicated Chrome user-data directory by copying an existing profile.

This is a safe helper for Playwright automation: copy a profile folder
from your system Chrome into a repo-local folder and use that as
`CHROME_USER_DATA_DIR` to avoid DevTools/profile-lock issues.
"""
from pathlib import Path
import shutil
import argparse
import sys

IGNORED_NAMES = {"SingletonLock", "LOCK", "Local State", "Local State-journal"}

def _ignore(src, names):
    # Ignore common lock/state files that cause issues when copied or locked
    return {n for n in names if n in IGNORED_NAMES or n.endswith('.lock')}

def main():
    p = argparse.ArgumentParser(description="Copy a Chrome profile to a dedicated user-data dir")
    p.add_argument("source", help="Path to the source Chrome profile folder (e.g. 'C:/Users/You/AppData/.../Profile 5')")
    p.add_argument("--dest-root", default="data/chrome_user_data", help="Destination root to place copied profiles")
    p.add_argument("--profile-name", default=None, help="Name to use for the copied profile folder (defaults to source folder name)")
    p.add_argument("--overwrite", action="store_true", help="Remove destination if it exists and copy fresh")
    args = p.parse_args()

    src = Path(args.source).expanduser().resolve()
    dest_root = Path(args.dest_root).expanduser().resolve()
    if not src.exists() or not src.is_dir():
        print(f"Source profile folder not found: {src}")
        sys.exit(2)

    profile_name = args.profile_name or src.name
    dest = dest_root / profile_name

    if dest.exists():
        if args.overwrite:
            print(f"Removing existing destination {dest} (overwrite requested)")
            shutil.rmtree(dest)
        else:
            print(f"Destination already exists: {dest}. Use --overwrite to replace")
            sys.exit(3)

    dest_root.mkdir(parents=True, exist_ok=True)
    try:
        print(f"Copying from {src} to {dest} (this may take a while)")
        shutil.copytree(src, dest, ignore=_ignore)
    except Exception as e:
        print(f"Failed to copy profile: {e}")
        sys.exit(4)

    print("Copy completed.")
    print("Set CHROME_USER_DATA_DIR to the copied root (example):")
    print(dest_root)

if __name__ == '__main__':
    main()
