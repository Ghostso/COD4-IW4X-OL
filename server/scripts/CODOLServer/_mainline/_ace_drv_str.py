import pefile, os, re

paths = {
 "ACE-BASE":   r"C:\Windows\system32\drivers\ACE-BASE.sys",
 "ACE-GAME":   r"C:\Windows\system32\drivers\ACE-GAME.sys",
 "ACE-ADVT":   r"C:\Windows\system32\drivers\ACE-ADVT.sys",
 "ACE-CORE203":r"C:\Program Files\AntiCheatExpert\ACE-CORE203.sys",
 "ACE-SSC-DRV64":r"C:\Program Files\AntiCheatExpert\SGuard\x64\Plugins\ACE-SSC-DRV64.sys",
}
for tag,p in paths.items():
    if not os.path.isfile(p): print("MISSING",tag); continue
    d=open(p,"rb").read()
    print("="*70)
    print("%s  %s  %d bytes"%(tag, os.path.basename(p), len(d)))
    # 设备名 / 符号链接 / 报告字符串
    seen=set()
    for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
        s=m.group().decode("latin1")
        low=s.lower()
        if any(k in low for k in ("\\device\\","\\dosdevices\\","\\??\\","bugcheck","dogfood","ping","heartbeat",
                                  "ioctl","seclogon","antich","sguard","ace-","report","url","http")):
            if s in seen: continue
            seen.add(s)
            print("   off 0x%06X %r"%(m.start(), s[:130]))
            if len(seen)>28: break
