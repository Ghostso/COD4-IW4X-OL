#!/usr/bin/env python3
"""Replace 1x1 TPFUI placeholder PNGs with valid transparent PNGs.

The shipped sandbox uses 69-byte 1x1 PNGs for almost every TPFUI image.  The
layouts crop those images into regions such as 240x28 and 228x24, so the
renderer logs LoadImageFromBuffer failures even though the files are valid
PNGs.  This script keeps the file names but gives each placeholder enough
space for the declared crops.

Usage:
  python -X utf8 CODOLServer/_mainline/_gen_tpfui_placeholders.py \
      run_codol_001/sandbox_ifs1_20260923/IIPS/TPFUI/IIPSRes
"""
import os
import sys

from PIL import Image


SIZE = (512, 512)


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else (
        r"run_codol_001\sandbox_ifs1_20260923\IIPS\TPFUI\IIPSRes"
    )
    if not os.path.isdir(root):
        print("missing root:", root, file=sys.stderr)
        return 2

    replaced = 0
    created = 0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(dirpath, name)
            if os.path.getsize(path) > 69:
                continue
            Image.new("RGBA", SIZE, (0, 0, 0, 0)).save(path, "PNG")
            replaced += 1

    # Referenced by SystemSetting.tpf but absent from the sandbox.
    missing = os.path.join(root, "back", "SystemSetting", "下载器设定底图.png")
    if not os.path.exists(missing):
        os.makedirs(os.path.dirname(missing), exist_ok=True)
        Image.new("RGBA", SIZE, (0, 0, 0, 0)).save(missing, "PNG")
        created += 1

    print("replaced=%d created=%d root=%s" % (replaced, created, root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
