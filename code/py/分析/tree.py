import os
import sys

sys.stdout.reconfigure(encoding="utf-8")


def walk(root, limit=400):
    shown = 0
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        print("[dir] %s  (%d files, %d dirs)" % (rel, len(files), len(dirs)))
        for name in sorted(files):
            path = os.path.join(base, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = -1
            print("      %10d  %s" % (size, name))
            shown += 1
            if shown >= limit:
                print("      ... truncated at %d files" % limit)
                return


for root in sys.argv[1:]:
    print("##### %s" % root)
    walk(root)
