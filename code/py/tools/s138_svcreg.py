#!/usr/bin/env python3
"""s138_svcreg: 找 {u32 svc, ptr code} 或 {ptr code, u32 svc} 的服务注册表, 连续>=4 条."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

def is_code(v): return v is not None and TL <= v < TH

for order in ("svc,fn", "fn,svc"):
    print("=== order %s ===" % order)
    runs = []
    o = 0
    while o < N - 8:
        a = u32(o); b = u32(o + 4)
        ok = False
        if order == "svc,fn":
            ok = (a is not None and 0 <= a <= 200) and is_code(b)
        else:
            ok = is_code(a) and (b is not None and 0 <= b <= 200)
        if ok:
            # collect run stepping 8
            run = []
            p = o
            while p < N - 8:
                x = u32(p); y = u32(p + 4)
                if order == "svc,fn":
                    if not ((x is not None and 0 <= x <= 200) and is_code(y)): break
                else:
                    if not (is_code(x) and (y is not None and 0 <= y <= 200)): break
                run.append((p, x, y)); p += 8
            if len(run) >= 4:
                runs.append(run)
                o = p
                continue
        o += 4
    seen = set()
    for run in runs:
        key = run[0][0]
        if key in seen: continue
        seen.add(key)
        svcs = [r[1] if order == "svc,fn" else r[2] for r in run]
        print("  @file0x%07X VA0x%08X len=%d svcs=%s" % (run[0][0], run[0][0]+VA, len(run), svcs))
        fns = [r[2] if order == "svc,fn" else r[1] for r in run]
        print("      fns=%s" % [hex(f) for f in fns[:12]])
