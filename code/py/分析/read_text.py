import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")


def read_text(path):
    blob = open(path, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return blob.decode(encoding)
        except UnicodeDecodeError:
            pass
    return blob.decode("latin-1", errors="replace")


def expand(patterns):
    paths = []
    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            paths.extend(sorted(glob.glob(pattern, recursive=True)))
        else:
            paths.append(pattern)
    return paths


for path in expand(sys.argv[1:]):
    print("===== %s =====" % os.path.abspath(path))
    if not os.path.exists(path):
        print("[missing]")
        continue
    print(read_text(path))
