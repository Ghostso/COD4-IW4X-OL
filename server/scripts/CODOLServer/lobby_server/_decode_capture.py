"""Decode the captured /auth/ request body. ASCII only."""
import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
log = os.path.join(os.path.dirname(here), "logs", "lobby_probe.jsonl")

for line in open(log, encoding="utf-8"):
    o = json.loads(line)
    if o.get("event") != "http":
        continue
    print("=" * 72)
    print("peer        :", o.get("peer"))
    print("request     :", o.get("request_line"))
    for h in o.get("headers", []):
        print("  hdr       :", h)
    body = bytes.fromhex(o.get("body_hex") or "")
    print("body_len    :", o.get("body_len"))
    print("body_raw    :", body.decode("utf-8", "replace"))
    try:
        j = json.loads(body.decode("utf-8"))
        print("body_json   :")
        for k, v in j.items():
            print("   %-14s = %r" % (k, v))
            if isinstance(v, str) and v.startswith("{"):
                try:
                    print("   %-14s   -> nested %r" % ("", json.loads(v)))
                except Exception:
                    pass
    except Exception as e:
        print("json parse failed:", e)
