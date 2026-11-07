import os
import re
import struct

TARGETS = [
    r"run_codol_001\sandbox\codoMP_client_shipRetail.exe",
    r"run_codol_001\sandbox\codoMP_client_shipRetailBase.dll",
]

ASCII_TERMS = [b"100]", b"[100]", b"lobby", b"Lobby", b"LOBBY"]


def scan(path):
    size = os.path.getsize(path)
    print("=" * 80)
    print(path, "size", size)
    data = open(path, "rb").read()

    for term in ASCII_TERMS:
        idx = [m.start() for m in re.finditer(re.escape(term), data)]
        print(f"  ascii {term!r}: {len(idx)} hits")
        for i in idx[:20]:
            s = max(0, i - 80)
            e = min(len(data), i + 120)
            chunk = data[s:e]
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"    off=0x{i:X} {asc}")

    # UTF-16LE Chinese terms
    for zh in ("无法连接大厅服务", "无法连接", "大厅服务", "连接大厅"):
        needle = zh.encode("utf-16-le")
        idx = [m.start() for m in re.finditer(re.escape(needle), data)]
        print(f"  utf16 {zh!r}: {len(idx)} hits")
        for i in idx[:10]:
            s = max(0, i - 60)
            e = min(len(data), i + 140)
            try:
                txt = data[s:e].decode("utf-16-le", "replace")
            except Exception:
                txt = ""
            print(f"    off=0x{i:X} {txt!r}")


def main():
    for t in TARGETS:
        if os.path.exists(t):
            scan(t)
        else:
            print("MISSING", t)


if __name__ == "__main__":
    main()
