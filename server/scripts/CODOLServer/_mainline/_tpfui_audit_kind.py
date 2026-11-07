# Classify every TPFUI file in the live install: real asset vs 69-byte stub,
# and report which factory files are absent (especially Layout/*.tpf).
import os
import hashlib

LIVE = r"COD OL\IIPS\TPFUI"
FACTORY = r"工具\EX035_DIR\IIPS\TPFUI"

STUB_SHA = None


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()[:16]


def walk(root):
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        if rel == ".":
            rel = ""
        for name in files:
            yield (os.path.join(rel, name) if rel else name,
                   os.path.join(base, name))


def main():
    print("=== live tree: extension histogram ===")
    hist = {}
    stubs = []
    real = []
    for rel, path in walk(LIVE):
        ext = os.path.splitext(rel)[1].lower() or "(none)"
        hist[ext] = hist.get(ext, 0) + 1
        size = os.path.getsize(path)
        if size <= 128:
            stubs.append((rel, size))
        else:
            real.append((rel, size))
    for ext, count in sorted(hist.items()):
        print("  %-10s %d" % (ext, count))

    print()
    print("=== 69-byte stub group: distinct sha256 ===")
    groups = {}
    for rel, size in stubs:
        if size == 69:
            d = sha16(os.path.join(LIVE, rel))
            groups.setdefault(d, []).append(rel)
    for d, rels in groups.items():
        print("  sha256[:16]=%s  count=%d" % (d, len(rels)))
        for rel in rels[:3]:
            print("      e.g. %s" % rel)

    print()
    print("=== real (non-stub) files under IIPSRes ===")
    for rel, size in sorted(real):
        if rel.lower().startswith("iipsres"):
            print("  %8d  %s" % (size, rel))

    print()
    print("=== factory subdirectories ===")
    for base, dirs, files in os.walk(FACTORY):
        rel = os.path.relpath(base, FACTORY)
        print("  DIR %s  (%d files)  -> %s" % (
            rel, len(files), ", ".join(sorted(files)[:8])))

    print()
    print("=== live subdirectories ===")
    for base, dirs, files in os.walk(LIVE):
        rel = os.path.relpath(base, LIVE)
        print("  DIR %s  (%d files)  -> %s" % (
            rel, len(files), ", ".join(sorted(files)[:8])))


main()
