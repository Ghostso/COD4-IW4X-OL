import re
b=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
print("=== exe 内所有 dw_* 命令/dvar 名 ===")
seen=set()
for m in re.finditer(rb"(?:dw|DW)_[a-z0-9_]{3,50}", b):
    s=m.group().decode("latin1")
    if s in seen: continue
    seen.add(s)
    print("  VA 0x%08X  %s" % (0x714000+m.start(), s))
