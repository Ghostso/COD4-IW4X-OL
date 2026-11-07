import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

# drop the duplicate helper that would be shadowed anyway
helper = '''def copy_log_dir(rel: str, records: list) -> None:
    src = ROOT / rel
    if not src.is_dir():
        records.append({"path": rel, "status": "MISSING"})
        return
    n = 0
    for item in sorted(src.iterdir()):
        if item.is_file():
            copy_file(rel + "/" + item.name, records)
            n += 1
    if n == 0:
        records.append({"path": rel, "status": "EMPTY"})


'''
assert s.count(helper) == 1
s = s.replace(helper, "", 1)

old = '''    "CODOLServer/_mainline/archive_confirmed_20260928.py",
]'''
new = '''    "CODOLServer/_mainline/archive_confirmed_20260928.py",
    "CODOLServer/logs/PLAIN/plain_20260928_180337.jsonl",
    "CODOLServer/logs/PLAIN/echo_20260928_180902.jsonl",
    "CODOLServer/logs/PLAIN/len200_20260928_181151.jsonl",
    "CODOLServer/logs/PLAIN/frame24_20260928_181453.jsonl",
    "CODOLServer/logs/PLAIN/frame204_20260928_181756.jsonl",
    "CODOLServer/logs/PLAIN/frame204b_20260928_181807.jsonl",
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
