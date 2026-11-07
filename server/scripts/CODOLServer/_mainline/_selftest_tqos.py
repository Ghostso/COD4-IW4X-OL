import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import fake_tqos_server as F
req=bytes.fromhex("75720010000800030000000b000070a10000006400180000")
print("parse:",F.try_parse_ur(req))
for v in (0,1,2):
    r=F.build_response(req,v)
    print("variant",v,"len",len(r),r.hex(" "),"->",F.try_parse_ur(r))
