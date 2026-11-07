import re
p=r"COD OL\codoMP_client_shipRetail.exe"
d=open(p,"rb").read()
print("=== exe 内全部域名串 ===")
seen=set()
for m in re.finditer(rb"[A-Za-z0-9][A-Za-z0-9._-]{4,80}\.[A-Za-z]{2,10}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("demonware","activision","qq.com","blaze","cod","callofduty","tencent")):
        if s in seen: continue
        seen.add(s)
        print("  VA 0x%08X  %s"%(0x714000+m.start(), s))
print()
print("=== 含 blaze / demo / logon host 的串 ===")
for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if ("blaze" in low or "logonhost" in low or "lobbyhost" in low or "dwlogon" in low or "demo.activision" in low) and len(s)<160:
        print("  VA 0x%08X  %r"%(0x714000+m.start(), s[:130]))
