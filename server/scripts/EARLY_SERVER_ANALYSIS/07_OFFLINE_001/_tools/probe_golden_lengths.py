import sys, re, hashlib
kit = r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT"
sys.path.insert(0, kit)
import codol_crypto as cc
def L(b): return len(b), hashlib.sha256(b).hexdigest()
fr = cc.build_mission_session_object(True)
nm = cc.build_mission_session_object(False)
print("build_mission_session_object(True) len:", len(fr), hashlib.sha256(fr).hexdigest())
print("build_mission_session_object(False) len:", len(nm), hashlib.sha256(nm).hexdigest())
rec = cc.build_session_record(0x1122334455667788, (127,0,0,1), 28960, 0, 18, 1, "mp_crash_tropical", b"\x01"*16, 1000001)
print("build_session_record len:", len(rec), hashlib.sha256(rec).hexdigest())
# count golden hex in SessionGolden.cs
src = open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\src\Codol\SessionGolden.cs", encoding="utf-8").read()
for name in ("CA_GOLDEN","REC_GOLDEN","FR_GOLDEN","NM_GOLDEN"):
    m = re.search(name + r'\s*=\s*((?:"[0-9A-F]+"\s*\+?\s*)+);', src)
    hexs = "".join(re.findall(r'"([0-9A-F]+)"', m.group(1)))
    print(name, "hexchars:", len(hexs), "bytes:", len(hexs)//2)
