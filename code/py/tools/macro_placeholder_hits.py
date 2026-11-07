#!/usr/bin/env python3
"""统计 81 个 ${TIMESTAMP_PLACEHOLDER} 引用点里, 有几个同时引用了 ${CLIENT_IP_PLACEHOLDER} /
${TIMESTAMP_OFFSET(%d)}; 并统计 8 个 CLIENT_IP 引用点的上下文.
用于回答: "信封两个占位符是否成对出现".
"""
import struct, re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)

def out(s):
    sys.stdout.write(s.encode("ascii", "replace").decode("ascii") + "\n")

def refs(off):
    return [m.start() for m in re.finditer(re.escape(struct.pack("<I", off + VA)), d)]

TS = refs(0x9BB744)      # ${TIMESTAMP_PLACEHOLDER}
IP = refs(0x9B4CF8)      # ${CLIENT_IP_PLACEHOLDER}
TO = refs(0x9C6FC4)      # ${TIMESTAMP_OFFSET(%d)}

out("TS refs=%d  IP refs=%d  TO refs=%d" % (len(TS), len(IP), len(TO)))

def enclosing_fn(hit, limit=0x400):
    """往回找最近的 55 8b ec 函数入口."""
    lo = max(0, hit - limit)
    for k in range(hit, lo, -1):
        if d[k:k+3] == b"\x55\x8b\xec" and d[k-8:k] in (b"\xcc"*8,) or (d[k:k+3] == b"\x55\x8b\xec" and k > 0 and d[k-1:k] == b"\xcc"):
            return k
    return None

out("")
out("=== 每个 TS 引用点所在函数, 该函数内是否也引用 IP/TO ===")
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
fn_groups = {}
for h in TS:
    f = enclosing_fn(h)
    fn_groups.setdefault(f, []).append(h)
out("  TS 落在 %d 个函数内" % len(fn_groups))
both = 0
for f, hits in sorted(fn_groups.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
    if f is None:
        out("  函数未知: hits=%s" % [hex(h) for h in hits]); continue
    # 函数范围: 到下一个函数入口或首个 ret
    end = min(f + 0x800, N)
    seg = d[f:end]
    has_ip = any(0 <= h - f < len(seg) for h in IP)
    has_to = any(0 <= h - f < len(seg) for h in TO)
    if has_ip: both += 1
    out("  fn@0x%06X  TS×%d  IP=%s TO=%s" % (f, len(hits), "Y" if has_ip else "-", "Y" if has_to else "-"))
out("")
out("=> 同时含 TS+IP 的函数: %d" % both)

out("")
out("=== 8 个 IP 引用点上下文 (反汇编 16 字节) ===")
for h in IP:
    f = enclosing_fn(h)
    out("  IP-ref@0x%06X  fn=%s" % (h, hex(f) if f else "?"))
    code = d[max(0, h - 24): h + 32]
    base = max(0, h - 24)
    for ins in md.disasm(code, base + VA):
        line = "      0x%08X %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for m in re.finditer(r"0x([0-9a-f]{6,8})", ins.op_str):
            v = int(m.group(1), 16)
            if VA <= v < VA + N:
                e = d.find(b"\x00", v - VA)
                s = d[v-VA:e]
                if s and all(32 <= c < 127 for c in s) and len(s) > 2:
                    line += "   ; %r" % s.decode("latin1")[:80]
        out(line)
