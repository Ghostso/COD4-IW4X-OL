import sys, json
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import aes_schedule_hunt as A
p=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\ProtocalHandler.dll'
data=open(p,'rb').read()
found=[]
def log(m): print(m)
A.scan_chunk(data,0,found,log)
print('found',len(found))
for f in found: print(json.dumps(f))
