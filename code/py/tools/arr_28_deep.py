#!/usr/bin/env python3
"""28/4 ContentUnlock2 全报文解剖 + 28/1 任务参数全报文解剖。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def dump(svc, task, limit=2):
    print("\n########## %d/%d ##########" % (svc, task))
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        print("\n--- run=%s len=%d els=%d good=%s ---" % (r.get("run"), len(b), len(els), good))
        for i, (t, v) in enumerate(els):
            if t in (0x6B, 0x6C):
                cnt, body = v
                print("  #%02d 0x%02x ARRAY bytelen=%d count=%d body[:24]=%s" %
                      (i, t, len(body), cnt, body[:24].hex()))
                if t == 0x6C and len(body) >= 4 and len(body) % 4 == 0:
                    u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body), 4)]
                    print("      u32[0:12]=%s ... u32[-4:]=%s" % (u[:12], u[-4:]))
            elif isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                print("  #%02d 0x%02x %d (0x%X)" % (i, t, iv, int.from_bytes(v, "little")))
            elif isinstance(v, bytes):
                esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
                print("  #%02d 0x%02x len=%d %s" % (i, t, len(v), esc[:50]))
        seen += 1
        if seen >= limit:
            break


dump(28, 4, 2)
dump(28, 1, 4)

# 28/4 body 内容 ID 是否是固定集合
print("\n########## 28/4 的 127 个内容 ID 集合是否恒定 ##########")
sets = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x6C:
            cnt, body = v
            u = tuple(int.from_bytes(body[j:j+4], "little") for j in range(0, len(body), 4))
            sets[u] += 1
print("distinct ID-tuple = %d" % len(sets))
for k, n in sets.most_common(2):
    print("  x%d n_ids=%d ids=%s" % (n, len(k), list(k)[:20]))
