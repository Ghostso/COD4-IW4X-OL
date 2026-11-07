import re, struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
print("=== 搜 Live/Lobby/Online/Party 相关字符串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("live_","live","lobby","online","party","session","host","join")) and len(s)<60:
        if s in seen: continue
        seen.add(s)
        print("   0x%08X %r"%(base+m.start(), s))
        if len(seen)>60: break
