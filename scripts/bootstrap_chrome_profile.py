#!/usr/bin/env python3
"""Bootstrap a dedicated Chrome user-data directory by copying an existing profile.

This helper copies:
1. The selected profile directory (for example: `Profile 5`)
2. The user-data root "Local State" files required for cookie/session decryption

Without "Local State", copied profiles can fail with os_crypt/decryption errors.
"""
from pathlib import Path
import argparse
import shutil
import sys

IGNORED_NAMES = {"SingletonLock", "LOCK", "lockfile"}


def _ignore(_src, names):
    # Ignore lock artifacts only.
    return {name for name in names if name in IGNORED_NAMES or name.endswith(".lock")}


def _copy_local_state_files(source_root: Path, dest_root: Path) -> list[str]:
    copied: list[str] = []
    for filename in ("Local State", "Local State-journal"):
        src = source_root / filename
        if not src.exists():
            continue
        dst = dest_root / filename
        shutil.copy2(src, dst)
        copied.append(filename)
    return copied

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
    source_root = src.parent

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
        print(f"Copying profile from {src} to {dest} (this may take a while)")
        shutil.copytree(src, dest, ignore=_ignore)
        copied_state_files = _copy_local_state_files(source_root, dest_root)
    except Exception as e:
        print(f"Failed to copy profile: {e}")
        sys.exit(4)

    print("Copy completed.")
    if copied_state_files:
        print(f"Copied root state files: {', '.join(copied_state_files)}")
    else:
        print("Warning: Local State files were not found in source root; session decryption may fail.")
    print("Set CHROME_USER_DATA_DIR to the copied root (example):")
    print(dest_root)
    print("Set CHROME_PROFILE_DIRECTORY to:")
    print(profile_name)

if __name__ == '__main__':
    main()
