import hashlib, glob, os
want = "07642387e67016546a0a1bab53522fe29becf2990740ccaa55e37c8fdfa2115a"
orig = open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_hosts_snap\hosts.original","rb").read()
lb   = open(r"C:\Windows\System32\drivers\etc\hosts.legacybridge-backup","rb").read()
ics  = open(r"C:\Windows\System32\drivers\etc\hosts.ics","rb").read()

def h(b): return hashlib.sha256(b).hexdigest()

cands = {}
cands["orig"] = orig
cands["orig_LF"] = orig.replace(b"\r\n", b"\n")
cands["orig_uncomment_uhe"] = orig.replace(b"#23.77.15.30", b"23.77.15.30")
# LB block appended / prepended to orig, in various forms
LB_BLOCK = b"# LegacyBridge redirect - Apple hostnames resolved to this PC for the legacy-iOS test\r\n192.168.137.1 albert.apple.com\r\n192.168.137.1 deviceservices.apple.com\r\n192.168.137.1 configuration.apple.com\r\n"
for name, base in (("orig", orig),):
    cands[name+"_plus_LBblock"] = base + LB_BLOCK
    cands[name+"_plus_LBblock2"] = base.rstrip(b"\r\n") + b"\r\n" + LB_BLOCK
# ICS machine line
for line in ics.split(b"\r\n"):
    if b"mshome.net" in line:
        cands["orig_plus_"+line[:14].decode('latin1','ignore')] = orig.rstrip(b"\r\n")+b"\r\n"+line+b"\r\n"
# try each UHE backup
for p in sorted(glob.glob(r"C:\Windows\System32\drivers\etc\hosts_UHE_Backup\*.bak")):
    cands["uhe:"+os.path.basename(p)] = open(p,"rb").read()

found=False
for n,b in cands.items():
    if h(b)==want:
        print("MATCH ->", n, len(b)); found=True
print("target len=937; matched:", found)
print("candidate lengths:", {n:len(b) for n,b in cands.items() if abs(len(b)-937)<120})
