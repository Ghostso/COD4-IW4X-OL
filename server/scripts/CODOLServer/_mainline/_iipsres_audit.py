# Audit the TPFUI resource trees that IIPSHostApp loads:
#   original install, sandbox used by the working launch chain,
#   and the factory EX035_DIR backup.
import os

ROOTS = [
    r"COD OL\IIPS\TPFUI",
    r"run_codol_001\sandbox_ifs1_20260923\IIPS\TPFUI",
    r"工具\EX035_DIR\IIPS\TPFUI",
]


def main():
    for root in ROOTS:
        print("===== %s =====" % root)
        if not os.path.exists(root):
            print("MISSING")
            print()
            continue

        dir_count = 0
        file_count = 0
        total = 0
        tiny = []
        samples = []

        for base, dirs, files in os.walk(root):
            dir_count += len(dirs)
            for name in files:
                path = os.path.join(base, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                file_count += 1
                total += size
                if size <= 128:
                    tiny.append((size, path))
                if len(samples) < 20:
                    samples.append((size, path))

        print("dirs=%d files=%d total=%d" % (dir_count, file_count, total))
        print("tiny(<=128) count=%d" % len(tiny))
        for size, path in tiny[:20]:
            print("  TINY %6d  %s" % (size, path))
        print("samples:")
        for size, path in samples:
            print("  %8d  %s" % (size, path))
        print()


main()
