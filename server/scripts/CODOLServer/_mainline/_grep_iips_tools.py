import os

ROOT = "CODOLServer"
NEEDLES = [
    "IIPSFilelist", "IFS", "VFS", "extract", "IIPSDownload",
    "CreateIFSLibDll", "IFSReadFile", "IFS2",
]


def main():
    for base, dirs, files in os.walk(ROOT):
        if any(skip in base.lower() for skip in ("log", "_sub", "runs")):
            dirs[:] = []
            continue
        for name in files:
            if not name.lower().endswith((".py", ".md", ".txt")):
                continue
            path = os.path.join(base, name)
            try:
                text = open(path, "r", encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if any(n in line for n in NEEDLES):
                    print("%s:%d: %s" % (path, line_no, line[:220]))


main()
