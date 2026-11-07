import os, json, re, sys

ROOTS = [
    r"D:\BaiduNetdiskDownload\CODOL",
    "D:\\BaiduNetdiskDownload\\\u4f7f\u547d\u53ec\u5524OL",
    r"E:\CODOL_SANDBOX",
    r"E:\IW4X",
    r"G:\SteamLibrary\steamapps\common\Call of Duty Modern Warfare 2",
]
EXTS = {".ini", ".cfg", ".txt", ".log", ".xml", ".dat", ".json", ".jsonl", ".md", ".lst", ".vdf", ".key"}
PATTERNS = [
    ("dwauth", re.compile(r"dwauth", re.I)),
    ("auth_path", re.compile(r"/auth/", re.I)),
    ("dw_ticket", re.compile(r"DW-?Ticket", re.I)),
    ("auth_host", re.compile(r"auth_host", re.I)),
    ("lobby", re.compile(r"lobby", re.I)),
    ("dirlobby", re.compile(r"dirlobby", re.I)),
    ("qq_host", re.compile(r"\b[a-z0-9][a-z0-9\-\.]*\.qq\.com\b", re.I)),
]
LIMIT = 2 * 1024 * 1024


def main():
    counts = {name: 0 for name, _ in PATTERNS}
    hits = []
    files = 0
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in EXTS:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > LIMIT or os.path.getsize(p) == 0:
                        continue
                except OSError:
                    continue
                files += 1
                try:
                    with open(p, "rb") as fh:
                        data = fh.read()
                except OSError:
                    continue
                if b"\x00" in data[:4096]:
                    continue
                text = data.decode("utf-8", "replace")
                if text.count("\ufffd") > len(text) * 0.3:
                    continue
                lines = text.splitlines()
                for idx, line in enumerate(lines, 1):
                    for name, pat in PATTERNS:
                        if pat.search(line):
                            counts[name] += 1
                            hits.append({
                                "pattern": name,
                                "file": p,
                                "line": idx,
                                "text": line.strip()[:400],
                            })
    print("FILES_SCANNED=%d" % files)
    for name, _ in PATTERNS:
        print("COUNT %s = %d" % (name, counts[name]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_hunt_text_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"counts": counts, "files_scanned": files, "hits": hits}, fh, ensure_ascii=False, indent=1)
    print("WROTE=%s" % out)
    for h in hits[:400]:
        print("%s|%s|%d|%s" % (h["pattern"], h["file"], h["line"], h["text"]))


if __name__ == "__main__":
    main()
