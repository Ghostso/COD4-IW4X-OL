p = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data = open(p,"rb").read()
for off in (8679184, 8679288, 8679340, 8679396, 8698952, 8801752, 8804592, 8817368, 8678472):
    chunk = data[off:off+180]
    s = chunk.split(b"\x00")[0]
    try: t = s.decode("latin1")
    except: t = repr(s)
    print(off, "|", t)
print("=== bdDTLS strings ===")
import re
for m in re.finditer(rb"bdDTLS[^\x00]{0,60}", data):
    print(m.start(), m.group().decode("latin1"))
