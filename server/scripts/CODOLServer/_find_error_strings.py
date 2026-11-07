import os

ROOTS = [r"run_codol_001\sandbox", r"COD OL"]
TERMS = ["无法连接大厅服务", "无法连接", "大厅服务", "[100]", "100]"]
ENCODINGS = ["utf-8", "utf-16le", "gbk"]
SKIP_DIRS = {".git", "__pycache__"}
MAX = 180 * 1024 * 1024


def main():
    hits = []
    scanned = 0
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                p = os.path.join(dirpath, name)
                try:
                    if os.path.getsize(p) > MAX:
                        continue
                    data = open(p, "rb").read()
                except Exception:
                    continue
                scanned += 1
                for term in TERMS:
                    for enc in ENCODINGS:
                        try:
                            needle = term.encode(enc)
                        except Exception:
                            continue
                        if needle in data:
                            hits.append((term, enc, data.count(needle), p))
    print("scanned files:", scanned)
    for term, enc, n, p in hits:
        print(f"{term!r} {enc} count={n} {p}")
    print("total hits:", len(hits))


if __name__ == "__main__":
    main()
