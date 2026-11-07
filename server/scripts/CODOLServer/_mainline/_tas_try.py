import os,struct,sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts')
from tas_crypt import decrypt,encrypt,score,DEFAULT_KEY
files=[r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe',r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll']
data=open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\tasdata_sample.bin','rb').read()
keys=[]
for p in files:
    st=os.stat(p)
    ft=st.st_mtime_ns//100 + 116444736000000000
    k=struct.pack('<II',ft&0xffffffff,(ft>>32)&0xffffffff)
    keys.append((p,k))
keys.append(('default',DEFAULT_KEY))
for name,k in keys:
    for flag,fn in (('dec',decrypt),('enc',encrypt)):
        out=fn(k,data)
        print('%-14s %-3s score=%.3f key=%s head=%r'%(name,flag,score(out),k.hex(),out[:80]))
