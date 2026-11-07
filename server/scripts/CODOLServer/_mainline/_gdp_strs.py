import pefile, re
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
print("=== GDPLoader.dll 全部非证书类字符串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{3,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("digicert","verisign","symantec","thawte","microsoft.com","globalsign","ocsp","crl","pkiops")): continue
    if len(s)<3: continue
    if s in seen: continue
    seen.add(s)
    # 只打印有信息量的
    if any(k in low for k in ("tqos","gdp","qos","http","content","user-agent","host","cmd","pkg","body","head",
                              "ver","magic","json","xml","url","uri","path","get ","post","token","uin","key",
                              "timeout","retry","dns","connect","socket","error","fail","ok","sss")) or re.match(r'^[A-Z][A-Za-z0-9_]{4,}$', s):
        print("  off 0x%06X VA 0x%08X  %r"%(m.start(), ib+pe.get_rva_from_offset(m.start()), s[:120]))
