import os
import re

ROOTS = [
    r"run_codol_001\sandbox\IIPS",
    r"run_codol_001\sandbox\TCLS",
    r"run_codol_001\sandbox",
    r"TCLS",
]

TARGETS = [
    "116.130.224.66",
    "116.130.224.41",
    "116.130.229.168",
    "116.131.226.149",
    "81.71.56.168",
    "124.222.110.82",
    "101.35.50.98",
    "42.187.183.203",
]

SKIP_EXT = {".pdb", ".png", ".jpg", ".ico", ".mp3", ".dat", ".ifs", ".pak", ".etl", ".txt"}


def encodings(ip):
    b = ip.encode()
    return {
        "ascii": b,
        "utf16le": ip.encode("utf-16-le"),
        "dotted_list": b.split(b"."),
    }


def main():
    hits = {}
    scanned = 0
    for root in ROOTS:
        if not os.path.isdir(root):
            print("skip (missing):", root)
            continue
        for dirpath, _, files in os.walk(root):
            for name in files:
                p = os.path.join(dirpath, name)
                ext = os.path.splitext(name)[1].lower()
                if ext in SKIP_EXT:
                    continue
                try:
                    if os.path.getsize(p) > 80 * 1024 * 1024:
                        continue
                    data = open(p, "rb").read()
                except Exception:
                    continue
                scanned += 1
                for ip in TARGETS:
                    e = encodings(ip)
                    if e["ascii"] in data:
                        hits.setdefault(ip, []).append((p, "ascii"))
                    if e["utf16le"] in data:
                        hits.setdefault(ip, []).append((p, "utf16le"))
    print("files scanned:", scanned)
    print("\n===== hits =====")
    for ip in TARGETS:
        lst = hits.get(ip, [])
        print("-" * 20, ip, "hits:", len(lst))
        for p, enc in lst[:40]:
            print("   ", enc, p)


if __name__ == "__main__":
    main()
