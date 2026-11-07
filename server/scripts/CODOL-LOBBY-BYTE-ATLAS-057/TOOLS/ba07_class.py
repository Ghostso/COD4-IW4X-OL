# -*- coding: utf-8 -*-
"""BA-07 类解剖器: TD -> COL -> vftable -> 逐槽反汇编.

用法:
  python -I -B TOOLS/ba07_class.py 0x00A6F754 [更多 TD RVA...]
  python -I -B TOOLS/ba07_class.py --name dwRoomMessageStartGame
"""
import re
import struct
import sys

import capstone

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000
d = open(IMG, "rb").read()
N = len(d)
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def cstr(off, mx=400):
    e = d.find(b"\x00", off, off + mx)
    return d[off:e].decode("latin1", "replace") if e > 0 else ""


def u4(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def demangle(nm):
    """极简 MSVC 名解析: 只取类名与方法名."""
    s = nm
    if s.startswith(".?AV"):
        s = s[4:]
    elif s.startswith(".?AU"):
        s = s[4:]
    core = s.split("@@")[0]
    parts = core.split("@")
    cls = parts[-1] if parts else core
    meth = parts[0] if parts else ""
    return cls, meth, core


def find_col(td):
    """TD 的 RVA = td; COL 里存 TD 的 RVA 或 VA."""
    out = []
    for target in (td, td + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            col = i - 12
            if col >= 0 and u4(col) == 0:
                # COL: sig,offset,cd,td,chd
                out.append(col)
            i = d.find(pat, i + 1)
    return out


def vftables_for_col(col):
    """vftable = 存 COL 指针那个槽 +4."""
    out = []
    for target in (col, col + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            out.append(i + 4)
            i = d.find(pat, i + 1)
    return out


def disas(fn_va, limit=60):
    off = fn_va - BASE
    if not (0 <= off < N):
        return []
    out = []
    for ins in CS.disasm(d[off:off + 0xC00], fn_va):
        txt = "%s %s" % (ins.mnemonic, ins.op_str)
        # 注释: 立即数若是字符串则显示
        note = ""
        m = re.search(r"0x([0-9a-f]{6,8})", ins.op_str)
        if m:
            v = int(m.group(1), 16)
            if 0 <= v - BASE < N - 8:
                s = cstr(v - BASE, 80)
                if s and all(32 <= ord(c) < 127 for c in s) and len(s) >= 4:
                    note = '   ; "%s"' % s
        out.append((ins.address, ins.bytes.hex(), txt, note))
        if ins.mnemonic in ("ret", "retn") or len(out) >= limit:
            break
    return out


def dump_class(td_rva, label=""):
    nm = cstr(td_rva + 8, 300)
    cls, meth, core = demangle(nm)
    print("=" * 82)
    print("TD RVA 0x%08X  VA 0x%08X   %s" % (td_rva, td_rva + BASE, label))
    print("  原始字节: %s" % d[td_rva:td_rva + 16].hex(" "))
    print("  pVFTable = 0x%08X" % u4(td_rva))
    print("  name     = %s" % nm)
    print("  类名=%s   方法=%s" % (cls, meth))

    cols = find_col(td_rva)
    print("  COL 命中: %d" % len(cols))
    for col in cols[:4]:
        sig, offset, cd, tdf, chd = struct.unpack_from("<IIIII", d, col)
        print("    COL @0x%08X  sig=0x%X offset=0x%X cd=0x%X td=0x%X chd=0x%X"
              % (col, sig, offset, cd, tdf, chd))
        vts = vftables_for_col(col)
        print("      vftable 候选: %d" % len(vts))
        for vt in vts[:3]:
            # 数槽
            slots = []
            p = vt
            while p + 4 <= N:
                v = u4(p)
                if v and BASE + 0x1000 <= v < BASE + N:
                    slots.append(v)
                    p += 4
                else:
                    break
                if len(slots) > 200:
                    break
            print("      vftable RVA 0x%08X  %d 槽" % (vt, len(slots)))
            for i, v in enumerate(slots):
                print("        [%2d] 0x%08X" % (i, v))
    return dict(td=td_rva, cls=cls, meth=meth, cols=cols)


def find_td_by_name(pat):
    out = []
    for m in re.finditer(rb"\.\?A[VU][\x20-\x7E]{1,200}\x00", d):
        nm = m.group()[:-1].decode("latin1")
        if pat in nm:
            out.append((m.start() - 8, nm))
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: ba07_class.py <TD_RVA_hex|--name substring>")
        return
    if args[0] == "--name":
        for td, nm in find_td_by_name(args[1]):
            dump_class(td, nm)
    else:
        for a in args:
            dump_class(int(a, 16))


if __name__ == "__main__":
    main()
