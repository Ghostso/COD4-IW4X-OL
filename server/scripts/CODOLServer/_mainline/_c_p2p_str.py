import re
d=open(r"COD OL\IIPS\p2papp.dll","rb").read()
print("=== p2papp.dll 全部 p2p/API/网络 相关可读串 ===")
seen=set()
for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
    s=m.group().decode("latin1")
    low=s.lower()
    if any(k in low for k in ("p2p","setqq","getqq","api_","http://","https://","udp://","tcp:","tracker",
                              "announce","peer","seed","share","upload","download","vip","appid","app_id",
                              "business","token","key","sign","auth","stat","report","dht","magnet","bt")):
        if s in seen: continue
        seen.add(s)
        print("  off 0x%06X %r"%(m.start(), s[:140]))
        if len(seen)>110: break
