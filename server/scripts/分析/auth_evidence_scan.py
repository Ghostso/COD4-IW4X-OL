"""Separate CLIENT-ORIGINATED auth evidence from local test-server artifacts.

Question: does a real captured packet stream contain the POST /auth/ request
and the JSON keys the local mock server assumes? If the keys only ever appear
inside CODOLServer/lobby_server/*.jsonl (our own harness), they are NOT client
evidence.
"""
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

NEEDLES = [
    b"POST /auth/",
    b"/auth/",
    b"auth_task",
    b"iv_seed",
    b"identity",
    b"title_id",
    b"DW-Ticket-Seed",
    b"DW-Server-Ticket",
    b"lsg_server_ticket",
    b"X-TransactionID",
]

ROOTS = [
    "CODOLServer/lobby_server",
    "CODOLServer/_subagents",
    "CODOLServer/_mainline",
    "CODOLServer/experiments",
]


def scan(path):
    try:
        blob = open(path, "rb").read()
    except OSError:
        return None
    hits = {}
    for needle in NEEDLES:
        n = blob.count(needle)
        if n:
            hits[needle.decode("latin-1")] = n
    return hits


found = {}
for root in ROOTS:
    for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if not os.path.isfile(path):
            continue
        if os.path.getsize(path) > 60 * 1024 * 1024:
            continue
        hits = scan(path)
        if hits:
            found[path] = hits

for path in sorted(found):
    print("%s" % path)
    for key, count in sorted(found[path].items()):
        print("    %-18s x%d" % (key, count))

print()
print("files with hits: %d" % len(found))
