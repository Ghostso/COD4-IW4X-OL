import re
files = {
 "ACE-BASE":r"C:\Windows\system32\drivers\ACE-BASE.sys",
 "ACE-GAME":r"C:\Windows\system32\drivers\ACE-GAME.sys",
 "ACE-SSC-DRV64":r"C:\Program Files\AntiCheatExpert\SGuard\x64\Plugins\ACE-SSC-DRV64.sys",
 "ACE-ADVT":r"C:\Windows\system32\drivers\ACE-ADVT.sys",
 "ACE-CORE203":r"C:\Program Files\AntiCheatExpert\ACE-CORE203.sys",
}
# UTF-16 strings too (device names often UTF-16)
for tag,p in files.items():
    d=open(p,"rb").read()
    print("="*68); print(tag)
    seen=set()
    # UTF-16LE
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,}", d):
        s=m.group().decode("utf-16-le","replace")
        if s in seen: continue
        seen.add(s)
        low=s.lower()
        if any(k in low for k in ("\\device","\\dosdevice","\\??","ace","sguard","ssc","tssc","anti","cheat")):
            print("   [U16] off 0x%06X %r"%(m.start(), s[:110]))
    # UTF-16BE
    for m in re.finditer(rb"(?:\x00[\x20-\x7e]){4,}", d):
        s=m.group().decode("utf-16-be","replace")
        if s in seen: continue
        seen.add(s)
        low=s.lower()
        if any(k in low for k in ("\\device","\\dosdevice","\\??","ace","sguard","ssc","tssc")):
            print("   [U16BE] off 0x%06X %r"%(m.start(), s[:110]))
