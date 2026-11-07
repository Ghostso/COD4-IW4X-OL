#!/usr/bin/env python3
"""解析 ol-mod 权威黄金向量 FULL_DESCRIPTOR_HEX（21/1 createSession 会话描述符），
定位 0xD692ADAB / 0x8D51E398 的确切字段位置与邻居语义。"""
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

FULL = (
    "10416C776179736F66666C696E65000ADEC0ADDE0100100110416C776179736F"
    "66666C696E6500079B1FF0D60700000000070000000008000000000700000000"
    "070000000007000000000700000000130810000000" "A06763B65A6939F30776DAE5782E0434" +
    "070000000007000000000700000000070800000007FFFFFFFF071C0300000721"
    "0000000700000000070500000007000000000798E3518D0ADEC0ADDE00000000"
    "0700000000070000000000"
)
b = bytes.fromhex(FULL)
print("len = %d" % len(b))
good, els, why = G.parse(b)
print("parse good=%s why=%s elements=%d" % (good, why, len(els)))
for i, (t, v) in enumerate(els):
    if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
        iv = int.from_bytes(v, "little", signed=(t == 0x07))
        u = int.from_bytes(v, "little")
        note = ""
        if u == 0xD692ADAB:
            note = "  <<< MAGIC A query criterion"
        elif u == 0x8D51E398:
            note = "  <<< MAGIC B"
        elif u == 0xD6F01F9B:
            note = "  <<< 0xD6F01F9B (golden 变体)"
        print("  #%02d 0x%02x len=%d signed=%d unsigned=0x%X%s" % (i, t, len(v), iv, u, note))
    elif isinstance(v, bytes):
        esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
        print("  #%02d 0x%02x len=%d %s" % (i, t, len(v), esc[:60]))
    else:
        print("  #%02d 0x%02x %r" % (i, t, v))
