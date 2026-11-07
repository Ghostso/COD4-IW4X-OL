# Inspect IIPSFilelist.ini for TPFUI / IIPSRes entries and enumerate the
# IFS archives actually present locally.
import os

FILELIST = r"COD OL\IIPS\IIPSFilelist.ini"
DL_DIR = r"COD OL\IIPS\IIPSDownload"


def main():
    blob = open(FILELIST, "rb").read()
    text = None
    for enc in ("utf-16", "utf-8", "gbk"):
        try:
            text = blob.decode(enc)
            print("decoded as %s, bytes=%d" % (enc, len(blob)))
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        print("undecodable")
        return

    lines = text.splitlines()
    print("lines=%d" % len(lines))
    print("--- first 40 lines ---")
    for line in lines[:40]:
        print(line[:200])

    print()
    print("--- lines mentioning TPFUI / IIPSRes / .tpf ---")
    for i, line in enumerate(lines):
        low = line.lower()
        if "tpfui" in low or "iipsres" in low or ".tpf" in low or "layout" in low:
            print("%d: %s" % (i, line[:240]))

    print()
    print("--- IFS archives on disk ---")
    if os.path.isdir(DL_DIR):
        entries = []
        for base, dirs, files in os.walk(DL_DIR):
            for name in files:
                path = os.path.join(base, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                entries.append((size, path))
        entries.sort(reverse=True)
        print("count=%d total=%.2f GB" % (
            len(entries),
            sum(size for size, _ in entries) / (1024 ** 3)))
        for size, path in entries[:40]:
            print("%14d  %s" % (size, path))


main()
