import os

ROOT = "."
EXTS = (".zip", ".rar", ".7z", ".tar", ".gz", ".ifs", ".vfs", ".pak", ".tpf", ".tprj")


def main():
    hits = []
    for base, dirs, files in os.walk(ROOT):
        if any(skip in base.lower() for skip in (
                "\\.git", "\\node_modules", "\\$recycle.bin")):
            dirs[:] = []
            continue
        for name in files:
            if name.lower().endswith(EXTS):
                path = os.path.join(base, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                hits.append((size, path))

    hits.sort(key=lambda item: (-item[0], item[1]))
    print("archive/container hits=%d" % len(hits))
    for size, path in hits[:400]:
        print("%12d  %s" % (size, path))


main()
