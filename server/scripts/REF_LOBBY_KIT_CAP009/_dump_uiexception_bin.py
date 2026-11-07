# -*- coding: utf-8 -*-
"""从 lobby_tasks.bin 解出 71/7 UIException 的**完整**调用链。

日志(lobby_srv.log)里的 payload 会被截断; lobby_tasks.bin 是完整的:
    svc(1B) task(1B) len(u32 LE) payload(len)
71/7 的 payload 里嵌 base64 文本, 解码后就是异常的完整调用链。

用法: python _dump_uiexception_bin.py [lobby_tasks.bin]
"""
import base64
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "lobby_tasks.bin")
    raw = open(p, "rb").read()
    off = 0
    seen = {}
    n = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) != (71, 7):
            continue
        n += 1
        txt = pl.decode("latin1", "replace")
        for m in re.finditer(r"([A-Za-z0-9+/]{40,}={0,2})", txt):
            b = m.group(1)
            try:
                d = base64.b64decode(b + "=" * (-len(b) % 4)).decode("utf-8", "replace")
            except Exception:
                continue
            if "Error" not in d:
                continue
            d = d.strip()
            seen[d] = seen.get(d, 0) + 1
    print("71/7 共 %d 条, 去重异常 %d 条" % (n, len(seen)))
    for k, c in sorted(seen.items(), key=lambda kv: -kv[1]):
        print("%dx  %s" % (c, k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
