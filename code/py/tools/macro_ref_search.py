#!/usr/bin/env python3
"""对每个宏/占位符串, 找它的 4B LE 指针引用点 -> 定位替换引擎."""
import struct, re, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

targets = [
    b"${TIMESTAMP_PLACEHOLDER}", b"${CLIENT_IP_PLACEHOLDER}", b"${TIMESTAMP_OFFSET(%d)}",
    b"${TIMESTAMP}", b"${CODOID(%s)}", b"${CODOID(%llu)}", b"${ZONEID(%llu)}",
    b"${CODO_OPENID}", b"${TITLE_ID}", b"${CODO_NAME}", b"${CODO_LEVEL}",
    b"${CODO_ZONE}", b"${CODO_TCLS_ZONE}", b"${CODO_JUMP_SIGNATURE}",
]
for t in targets:
    off = d.find(t + b"\x00")
    if off < 0:
        out("%-26s <not found as own NUL string>" % t.decode())
        continue
    ptr = off + VA
    hits = [m.start() for m in re.finditer(re.escape(struct.pack("<I", ptr)), d)]
    out("%-26s str=0x%06X ptr=0x%06X refs=%d %s" %
        (t.decode(), off, ptr, len(hits), [hex(h) for h in hits[:10]]))
    # 若引用存在, 看引用点前 30 字节里是否有别的串 push
    for h in hits[:10]:
        pre = d[max(0, h - 40):h]
        names = []
        for k in range(len(pre) - 5, -1, -1):
            if pre[k] == 0x68:
                v = struct.unpack_from("<I", pre, k + 1)[0]
                if VA <= v < VA + N:
                    e = d.find(b"\x00", v - VA)
                    s = d[v - VA:e]
                    if s and all(32 <= c < 127 for c in s):
                        names.append(s.decode("latin1"))
                        break
        out("      ref@0x%06X  nearby-push=%s  bytes=%s" %
            (h, names, pre[-16:].hex()))
