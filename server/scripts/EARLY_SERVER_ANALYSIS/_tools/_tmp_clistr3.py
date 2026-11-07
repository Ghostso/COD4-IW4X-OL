import re
p = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data = open(p,"rb").read()
for pat in (rb"bdNATTrav[^\x00]{0,55}", rb"bdQoS[^\x00]{0,55}", rb"bdSecurityKey[^\x00]{0,40}", rb"bdLobbyService[^\x00]{0,40}", rb"bdConnectionStore[^\x00]{0,45}", rb"bdReference[^\x00]{0,40}"):
    print("=====", pat)
    seen=set()
    for m in re.finditer(pat, data):
        g = m.group().decode("latin1")
        if g in seen: continue
        seen.add(g)
        print(m.start(), g)
    print("count uniq", len(seen))
