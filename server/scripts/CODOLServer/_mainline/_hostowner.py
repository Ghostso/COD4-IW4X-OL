import os, sys
HOSTS = [
 "tqos.gamesafe.qq.com","down.qq.com","dump.gamesafe.qq.com","intldlgs.qq.com",
 "stat.iips.qq.com","stun1-tub.codol.qq.com","stun2-tub.codol.qq.com","stun3-tub.codol.qq.com",
 "ied-tqos.qq.com","tqm.gamebaby.qq.com","socket.hipcapi.com","lant.top","cdntips.net",
 "gamesafe.qq.com","gamebaby.qq.com","iips.qq.com","codol.qq.com","demo.activision.com","demonware.net",
]
ROOTS = [
 r"COD OL",
 r"C:\Program Files\AntiCheatExpert",
 r"C:\Program Files (x86)\AntiCheatExpert",
]
found = {h: [] for h in HOSTS}
scanned = 0
for R in ROOTS:
    if not os.path.isdir(R): continue
    for dp,_,fns in os.walk(R):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 120*1024*1024: continue
                d = open(p,"rb").read()
            except Exception: continue
            scanned += 1
            for h in HOSTS:
                hb = h.encode()
                if hb in d or h.encode("utf-16-le") in d:
                    found[h].append(p)
print("扫描文件数:", scanned)
print()
for h in HOSTS:
    fs = found[h]
    if fs:
        # 只显示相对路径的关键部分
        shown = "; ".join(os.path.basename(x) for x in fs[:4])
        print("%-30s 命中 %2d 个文件  -> %s"%(h, len(fs), shown))
    else:
        print("%-30s 命中 0"%h)
