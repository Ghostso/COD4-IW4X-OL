import re
d=open(r"COD OL\codoMP_client_shipRetailBase.dll","rb").read()
print("=== Base.dll 里 ACE 相关全部串（含 UTF-16）===")
seen=set()
pats=[rb"[\x20-\x7e]{5,}", rb"(?:[\x20-\x7e]\x00){5,}"]
for pi,pat in enumerate(pats):
    for m in re.finditer(pat, d):
        try:
            s = m.group().decode("latin1") if pi==0 else m.group().decode("utf-16-le","replace")
        except: continue
        low=s.lower()
        if any(k in low for k in ("ace-ats","ace-drv","anticheat","sguard","\\\\.\\ace","tvsd","tcj","tersafe",
                                  "CreateObject","DllEntry","GetObject")):
            if s in seen: continue
            seen.add(s)
            print("  [%s] off 0x%06X %r"%("A" if pi==0 else "U16", m.start(), s[:120]))
