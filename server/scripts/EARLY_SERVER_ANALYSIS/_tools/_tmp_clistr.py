import re, io, os
p = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data = open(p,"rb").read()
print("size", len(data))
pats = [b"challengeResponse", b"connectResponse", b"getchallenge", b"protocol\\", b"shortversion", b"sv_maxclients", b"clc_move", b"clc_clientCommand", b"iw4\\code_source", b"com_memory", b"codol", b"bdDTLS", b"bdNATTrav", b"bdQoS"]
for pt in pats:
    idxs = [m.start() for m in re.finditer(re.escape(pt), data)]
    print(pt.decode("latin1"), "->", len(idxs), idxs[:6])
