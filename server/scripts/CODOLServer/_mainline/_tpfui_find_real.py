# Find any real (non-69-byte) copies of the polluted TPFUI PNGs anywhere
# under the project tree.
import os

ROOT = "."
NAMES = [
    "暂停下载_1_按下.png",
    "边玩边下底.png",
    "下载器设定底图.png",
    "速度设置正常.png",
    "黄色进度条_头.png",
    "button.png",
]


def main():
    wanted = {name.lower() for name in NAMES}
    hits = []
    for base, dirs, files in os.walk(ROOT):
        # Keep the walk bounded to project-related trees.
        if any(skip in base.lower() for skip in (
                "\\.git", "\\node_modules", "\\$recycle.bin")):
            dirs[:] = []
            continue
        for name in files:
            if name.lower() not in wanted:
                continue
            path = os.path.join(base, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            hits.append((size, path))

    hits.sort(key=lambda item: (-item[0], item[1]))
    sizes = {}
    for size, _path in hits:
        sizes[size] = sizes.get(size, 0) + 1
    print("hits=%d  size histogram:" % len(hits))
    for size in sorted(sizes):
        print("  size=%d count=%d" % (size, sizes[size]))

    print("non-stub copies (>128 bytes):")
    found = 0
    for size, path in hits:
        if size > 128:
            print("%10d  %s" % (size, path))
            found += 1
    print("non-stub count=%d" % found)


main()
