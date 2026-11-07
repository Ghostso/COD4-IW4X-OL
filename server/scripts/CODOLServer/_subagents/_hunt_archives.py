import os, sys, zipfile, json

ROOTS = ["C:\\", "D:\\", "E:\\", "F:\\", "G:\\"]
EXT = {".zip", ".rar", ".7z", ".tar", ".gz"}
KEY = ("cod", "ol", "iw4", "\u4f7f\u547d\u53ec\u5524")


def name_matches(path):
    low = path.lower()
    if "cod" in low or "iw4" in low:
        return True
    base = low.replace("\\", "/")
    if "ol" in [p for p in base.replace(".", "/").split("/")]:
        return True
    return "\u4f7f\u547d\u53ec\u5524" in path


def main():
    archives = []
    for r in ROOTS:
        for dirpath, dirnames, filenames in os.walk(r, onerror=lambda e: None):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in EXT:
                    archives.append(os.path.join(dirpath, fn))
    matched = [p for p in archives if name_matches(p)]
    print("TOTAL_ARCHIVES=%d" % len(archives))
    print("MATCHED_NAMES=%d" % len(matched))
    results = []
    for p in matched:
        entry = {"archive": p, "dwauth": [], "status": "not-opened"}
        if p.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(p) as z:
                    names = z.namelist()
                    entry["status"] = "ok"
                    entry["entries"] = len(names)
                    entry["dwauth"] = [n for n in names if "dwauth" in n.lower()]
                    entry["inis"] = [n for n in names if n.lower().endswith((".ini", ".cfg"))][:40]
            except Exception as exc:
                entry["status"] = "error: %s" % exc
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_hunt_archives_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    print("WROTE=%s" % out)


if __name__ == "__main__":
    main()
