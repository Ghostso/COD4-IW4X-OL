import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import suspend_host_redirect as S
req=bytes.fromhex('75720010000800030000000b000001d30000006400180000')
for v in (3,4,5):
    r=S.build_tqos_response(req,v)
    print('variant',v,'len',len(r))
    print('  ',r.hex(' '))
