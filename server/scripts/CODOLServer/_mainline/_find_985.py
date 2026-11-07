import os
import re

ROOTS = [
    r"COD OL\IIPS",
    r"run_codol_001\runs",
]

PATTERNS = [
    "985",
    "Can't find Component",
    "Creator From Dll List",
]


def main():
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for base, dirs, files in os.walk(root):
            for name in files:
                if not name.lower().endswith((".log", ".txt", ".ini")):
                    continue
                path = os.path.join(base, name)
                try:
                    blob = open(path, "rb").read()
                except OSError:
                    continue
                text = None
                for enc in ("utf-16", "utf-8", "gbk"):
                    try:
                        text = blob.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if text is None:
                    continue
                for needle in ("Can't find Component", "Creator From Dll List"):
                    if needle in text:
                        for line in text.splitlines():
                            if needle in line:
                                print("%s  ::  %s" % (path, line.strip()[:220]))


main()
