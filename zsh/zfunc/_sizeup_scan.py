#!/usr/bin/env python3
"""
Collect directory statistics for sizeup --explain.

Outputs a JSON object with rounding and skipped-path metadata.
"""

import json
import os
import stat
import sys
from typing import Dict, List


def round512(value: int) -> int:
    return ((value + 511) // 512) * 512


def scan(root: str) -> Dict[str, object]:
    file_round512 = 0
    file_round_alloc = 0
    dir_size = 0
    dir_round512 = 0
    dir_alloc = 0
    special_size = 0
    special_alloc = 0

    skipped: List[str] = []
    seen_inodes = set()

    walker = os.walk(
        root,
        followlinks=False,
        onerror=lambda err: skipped.append(getattr(err, "filename", str(err))),
    )

    for dirpath, dirnames, filenames in walker:
        try:
            st_dir = os.lstat(dirpath)
        except (FileNotFoundError, PermissionError, OSError):
            skipped.append(dirpath)
            continue

        size = st_dir.st_size
        alloc = st_dir.st_blocks * 512
        dir_size += size
        dir_alloc += alloc
        dir_round512 += max(round512(size) - size, 0)

        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                st = os.lstat(path)
            except (FileNotFoundError, PermissionError, OSError):
                skipped.append(path)
                continue

            mode = st.st_mode
            if stat.S_ISREG(mode):
                inode_key = (st.st_dev, st.st_ino)
                if inode_key in seen_inodes:
                    continue
                seen_inodes.add(inode_key)
                size = st.st_size
                alloc = st.st_blocks * 512
                file_round512 += max(round512(size) - size, 0)
                file_round_alloc += max(alloc - size, 0)
            elif stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
                size = st.st_size
                alloc = st.st_blocks * 512
                special_size += size
                special_alloc += alloc

    return {
        "file_rounding_bytes": file_round512,
        "file_round_alloc_bytes": file_round_alloc,
        "dir_bytes": dir_size,
        "dir_rounding_bytes": dir_round512,
        "dir_alloc_bytes": dir_alloc,
        "special_total": special_size,
        "special_alloc_bytes": special_alloc,
        "skipped_paths": skipped,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: _sizeup_scan.py <path>", file=sys.stderr)
        return 1

    root = sys.argv[1]
    if not os.path.exists(root):
        print(json.dumps({"error": f"path not found: {root}"}))
        return 0

    data = scan(root)
    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
