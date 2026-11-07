#!/usr/bin/env python3
"""B7: 试 undname 各种变体, 找能被反解的形态."""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UND = r"E:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx86\x86\undname.exe"

tests = [
    "?AVValue@GFx@Scaleform@@",
    ".?AVValue@GFx@Scaleform@@",
    "?AUOnPveModeClick_SF_Handler@?BH@??Init@UiCppMatchSelectView@@QAEXAAVValue@GFx@Scaleform@@@Z@",
    ".?AUOnPveModeClick_SF_Handler@?BH@??Init@UiCppMatchSelectView@@QAEXAAVValue@GFx@Scaleform@@@Z",
    ".?AUOnPveModeClick_SF_Handler@?BH@??Init@UiCppMatchSelectView@@QAEXAAVValue@GFx@Scaleform@@@Z@",
    ".?AUAS_OnInit_SF_Handler@?1??Init@UiCppView@@QAEXAAVValue@GFx@Scaleform@@@Z@",
    "?AUAS_OnInit_SF_Handler@?1??Init@UiCppView@@QAEXAAVValue@GFx@Scaleform@@@Z",
]
for t in tests:
    try:
        r = subprocess.run([UND, "/show", t], capture_output=True, text=True, timeout=20)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as ex:
        out = "ERR %s" % ex
    # 只打印最后一行(is :-)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    tail = lines[-1] if lines else ""
    print("IN : %s" % t)
    print("OUT: %s" % tail)
    print()
