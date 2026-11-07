import re
d=open(r"COD OL\codoMP_client_shipRetailBase.dll","rb").read()
print("=== Base.dll: 配置/注册表/键名 相关串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("software\\","\\tencent","\\tenprotect","\\tas","loadtype","enable","disable",
                              "loaddriver","optio n","option","setting","config","\\registry","hkey",
                              "m_b","m_dw","g_b","g_dw")):
        if any(x in low for x in ("digicert","verisign","microsoft.com","symantec","thawte","globalsign")): continue
        if s in seen: continue
        seen.add(s)
        print("  off 0x%06X %r"%(m.start(), s[:130]))
        if len(seen)>70: break
print()
print("=== UTF-16 注册表路径 ===")
seen2=set()
for m in re.finditer(rb"(?:[\x20-\x7e]\x00){6,}", d):
    s=m.group().decode("utf-16-le","replace")
    low=s.lower()
    if any(k in low for k in ("software\\","tencent","tenprotect","\\tas","registry","hkey")):
        if s in seen2: continue
        seen2.add(s); print("  off 0x%06X %r"%(m.start(), s[:130]))
        if len(seen2)>25: break
