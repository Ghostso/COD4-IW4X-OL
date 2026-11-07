# -*- coding: utf-8 -*-
import struct
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
RES = 0x0E5C9000
RESTYPE = {3: "ICON", 6: "STRINGTABLE", 14: "GROUP_ICON", 16: "VERSION",
           24: "MANIFEST"}
LANG = {0x409: "en-US", 0x804: "zh-CN", 0x404: "zh-TW", 0x411: "ja-JP",
        0x412: "ko-KR"}


def walk(dir_off, depth=0, path=()):
    o = RES + dir_off
    ch, ts, maj, mnr, nn, ni = struct.unpack_from("<IIHHHH", d, o)
    for i in range(nn + ni):
        nm, off = struct.unpack_from("<II", d, o + 16 + i * 8)
        isdir = bool(off & 0x80000000)
        sub = off & 0x7FFFFFFF
        ident = nm if not (nm & 0x80000000) else "name@%d" % (nm & 0x7FFFFFFF)
        if isdir:
            walk(sub, depth + 1, path + (ident,))
        else:
            do = RES + sub
            rva, sz, cp = struct.unpack_from("<III", d, do)
            leaf = d[rva:rva + sz]
            p = "\\".join(str(x) for x in path + (ident,))
            label = ""
            top = path[0] if path else None
            if top == 24:
                label = leaf.decode("latin1", "replace")
            elif top == 16:
                label = parse_version(leaf)
            elif top == 6:
                label = parse_strtable(leaf)
            elif top == 3:
                label = "icon %d bytes, %dx%d" % (sz, leaf[4] if len(leaf) > 4 else -1,
                                                  leaf[6] if len(leaf) > 6 else -1)
            elif top == 14:
                label = "groupicon " + leaf[:16].hex(" ")
            print("  [%-10s] %-24s rva=0x%08X sz=%-6d cp=%d" %
                  (RESTYPE.get(top, str(top)), p, rva, sz, cp))
            if label:
                for ln in str(label).splitlines():
                    print("        | " + ln)


def parse_version(b):
    # VS_VERSIONINFO
    if not b:
        return ""
    import re
    out = []
    for enc in ("utf-16-le",):
        try:
            s = b.decode(enc, "ignore")
        except Exception:
            s = ""
        for m in re.finditer(r"[\x20-\x7E]{3,}", s):
            out.append(m.group())
    return "\n".join(out[:40])


def parse_strtable(b):
    out = []
    for i in range(16):
        n = struct.unpack_from("<H", b, i * 2)[0]
        if n:
            s = b[i * 2 + 2:i * 2 + 2 + n * 2].decode("utf-16-le", "ignore")
            out.append("[%2d] %s" % (i, s))
    return "\n".join(out)


walk(0)
