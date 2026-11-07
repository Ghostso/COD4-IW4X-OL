import os
import re

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
ORIG = r"COD OL\IIPS"

TERMS = [
    "Component(985)",
    "Can't find Component",
    "Creator From Dll List",
    "985",
]


def scan_dir(root, label):
    print("=" * 80)
    print(label, root)
    if not os.path.isdir(root):
        print("  (missing)")
        return
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        size = os.path.getsize(p)
        if size > 40 * 1024 * 1024:
            continue
        try:
            data = open(p, "rb").read()
        except Exception:
            continue
        hits = []
        for term in TERMS:
            for enc in ("ascii", "utf-16le"):
                try:
                    needle = term.encode(enc)
                except Exception:
                    continue
                n = data.count(needle)
                if n:
                    hits.append(f"{term!r}/{enc}={n}")
        if hits:
            print(f"  {name} ({size}): {', '.join(hits)}")


def main():
    scan_dir(IIPS, "SANDBOX")
    scan_dir(ORIG, "ORIGINAL")

    print("\n########## Tenio component ids near 985 ##########")
    target = os.path.join(IIPS, "IIPSHost.dll")
    if not os.path.exists(target):
        target = os.path.join(IIPS, "IIPSHostApp.exe")
    data = open(target, "rb").read()
    for m in re.finditer(rb"\[Tenio_Error\][^\x00]{0,120}", data):
        print("  format:", m.group(0).decode("latin-1"))
    for m in re.finditer(rb"[A-Za-z0-9_./]{3,60}\.dll", data):
        s = m.group(0).decode("latin-1")
        print("  dllref:", s)


if __name__ == "__main__":
    main()
