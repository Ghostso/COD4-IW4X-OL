#!/usr/bin/env python3
"""B7: 用 undname 反解合成 mangled 名, 确定数字编码与 ?/@ 终止符规则."""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"


def und(m):
    try:
        r = subprocess.run([UND, m], capture_output=True, text=True, timeout=20)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as ex:
        return "ERR %s" % ex
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-1] if lines else ""


NUMS = ["0", "1", "2", "3", "9", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "Z",
        "10", "11", "19", "1A", "A0", "AA", "1", "9"]

print("=== 合成: ?AUDummy@?<N><sep>?bar@@YAXXZ ===")
print("%-6s %-4s %-6s %s" % ("N", "sep", "label", "result"))
for N in NUMS:
    for sep in ("?", "@"):
        name = "?AUDummy@?%s%s?bar@@YAXXZ" % (N, sep)
        tail = und(name)
        lab = re.findall(r"`(\d+)'", tail)
        ok = "OK" if "dummy" in tail.lower() or "Dummy" in tail else ""
        print("%-6s %-4s %-6s %s" % (N, "?" if sep == "?" else "@",
                                     lab[0] if lab else "-", tail[-60:]))
    print()
