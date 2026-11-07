import re, os
files = {
 "ACE-BASE":r"C:\Windows\system32\drivers\ACE-BASE.sys",
 "ACE-GAME":r"C:\Windows\system32\drivers\ACE-GAME.sys",
 "ACE-ADVT":r"C:\Windows\system32\drivers\ACE-ADVT.sys",
 "ACE-CORE203":r"C:\Program Files\AntiCheatExpert\ACE-CORE203.sys",
 "ACE-SSC-DRV64":r"C:\Program Files\AntiCheatExpert\SGuard\x64\Plugins\ACE-SSC-DRV64.sys",
}
pat = re.compile(rb"[\x20-\x7e]{5,}")
for tag,p in files.items():
    d=open(p,"rb").read()
    hits=[]
    for m in pat.finditer(d):
        s=m.group().decode("latin1")
        low=s.lower()
        if any(k in low for k in ("bugcheck","bug check","\\device","\\dosdevice","\\??\\","symboliclink",
                                  "ssc","heartbeat","ping","dogfood","anti","cheat","ace","sguard","minifilter",
                                  "altitude","callback","notify","obregister","handle")):
            if "digicert" in low or "microsoft.com" in low or "verisign" in low: continue
            hits.append((m.start(), s))
    print("="*68); print(tag, os.path.basename(p), "hits", len(hits))
    for o,s in hits[:30]:
        print("   off 0x%06X %r"%(o, s[:120]))
