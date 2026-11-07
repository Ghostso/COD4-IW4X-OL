import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

old = '''    "AUTO_LOBBY_20260928_180032_r1",  # lobby connect lands on HTTPS probe as plain TCP
    "AUTO_LOBBY_20260928_180920_r1",
    "AUTO_LOBBY_20260928_181236_r2",
    "AUTO_LOBBY_20260928_181603_r3",
    "AUTO_LOBBY_20260928_181937_r4",
]'''
new = '''    "AUTO_LOBBY_20260928_180032_r1",  # lobby connect lands on HTTPS probe as plain TCP
    "AUTO_LOBBY_20260928_180413_r2",
    "AUTO_LOBBY_20260928_180938_r2",
    "AUTO_LOBBY_20260928_181229_r2",
    "AUTO_LOBBY_20260928_181556_r3",
    "AUTO_LOBBY_20260928_181930_r4",
]

# Raw plain-TCP lobby channel captures (the decisive protocol evidence).
PLAIN_DIR = "CODOLServer/logs/PLAIN"
PLAIN_LOGS = [
    "plain_20260928_180337.jsonl",   # first 28-byte lobby probe packet
    "echo_20260928_180902.jsonl",    # echo -> client advances to sub-state 3
    "len200_20260928_181151.jsonl",  # 200-byte padded frame accepted
    "frame24_20260928_181453.jsonl", # len=24 frame rejected
    "frame204_20260928_181756.jsonl",
    "frame204b_20260928_181807.jsonl",
]'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

# add a copy_log_dir helper + wire PLAIN_DIR copy where LOG_DIRS is used
anchor = "def copy_file(rel: str, records: list) -> None:"
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
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
