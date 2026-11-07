# Compare the polluted live TPFUI tree against the factory EX035_DIR tree,
# and against the sandbox copy, to enumerate exactly what to restore.
import os
import hashlib

PAIRS = [
    (r"COD OL\IIPS\TPFUI", r"工具\EX035_DIR\IIPS\TPFUI", "live vs factory"),
    (r"run_codol_001\sandbox_ifs1_20260923\IIPS\TPFUI",
     r"工具\EX035_DIR\IIPS\TPFUI", "sandbox vs factory"),
]


def index(root):
    out = {}
    for base, dirs, files in os.walk(root):
        rel_base = os.path.relpath(base, root)
        if rel_base == ".":
            rel_base = ""
        for name in files:
            path = os.path.join(base, name)
            rel = os.path.join(rel_base, name) if rel_base else name
            out[rel] = path
    return out


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    for left_root, right_root, label in PAIRS:
        print("===== %s =====" % label)
        print("  L=%s" % left_root)
        print("  R=%s" % right_root)
        if not (os.path.isdir(left_root) and os.path.isdir(right_root)):
            print("  MISSING")
            print()
            continue
        left = index(left_root)
        right = index(right_root)

        only_left = sorted(set(left) - set(right))
        only_right = sorted(set(right) - set(left))
        common = sorted(set(left) & set(right))

        differing = []
        for rel in common:
            lsize = os.path.getsize(left[rel])
            rsize = os.path.getsize(right[rel])
            if lsize != rsize:
                differing.append((rel, lsize, rsize))
            elif digest(left[rel]) != digest(right[rel]):
                differing.append((rel, lsize, rsize))

        print("  only in LEFT  (%d):" % len(only_left))
        for rel in only_left[:40]:
            print("    %s" % rel)
        print("  only in RIGHT (%d)  = MISSING FROM LEFT:" % len(only_right))
        for rel in only_right[:60]:
            print("    %s  (%d bytes)" % (rel, os.path.getsize(right[rel])))
        print("  differing content (%d):" % len(differing))
        for rel, lsize, rsize in differing[:40]:
            print("    %s  L=%d R=%d" % (rel, lsize, rsize))
        print()


main()
