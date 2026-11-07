#!/usr/bin/env python3
"""dump 我们语料里 21/5 的完整报文，确认魔数 A 的确切位置与上下文。"""
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
A = 0xD692ADAB

shown = 0
for r in corpus:
    if (r["svc"], r["task"]) != (21, 5):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    hasA = any(isinstance(v, bytes) and len(v) == 4 and int.from_bytes(v, "little") == A
               for t, v in els)
    print("\n=== 21/5 run=%s len=%d els=%d hasA=%s ===" % (r.get("run"), len(b), len(els), hasA))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            u = int.from_bytes(v, "little")
            note = " <<< MAGIC A" if u == A else ""
            print("  #%02d 0x%02x %d 0x%X%s" % (i, t, iv, u, note))
        elif isinstance(v, bytes):
            esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
            print("  #%02d 0x%02x len=%d %s" % (i, t, len(v), esc[:40]))
        else:
            print("  #%02d 0x%02x %r" % (i, t, v))
    shown += 1
    if shown >= 4:
        break
