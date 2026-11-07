import re
for f in [r"COD OL\GDPLoader.dll", r"COD OL\GameDataPlatformServer.dll", r"COD OL\GDPImpl.dll"]:
    try: d=open(f,"rb").read()
    except: continue
    print("="*60); print(f, len(d))
    seen=set()
    for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
        s=m.group().decode("latin1")
        low=s.lower()
        if any(k in low for k in ("gamesafe","tqos","gdp","lobby","http://","https://","qq.com","host","port","iplist","server")):
            if s in seen: continue
            seen.add(s)
            print("   %r"%s[:130])
            if len(seen)>28: break
