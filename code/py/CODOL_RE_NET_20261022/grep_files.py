import os,re
root=r'COD OL'
keys=[b'formal-zone',b'codol.qq.com',b'dwauth.ini',b'iips.ini',b'stun.ini',b'VSDDrvDll',b'TenRpcs',b'GameRpcs',b'TenProxy',b'ace-ats32',b'TCLS_SHAREDMEMORY',b'vWINHTTP',b'3074']
files=[f for f in os.listdir(root) if f.lower().endswith(('.dll','.exe','.ini','.dat'))]
for f in files:
    p=os.path.join(root,f)
    try:
        if os.path.getsize(p)>80_000_000: continue
        d=open(p,'rb').read()
    except: continue
    hits=[]
    for k in keys:
        n=d.count(k)
        if n: hits.append('%s=%d'%(k.decode(),n))
    if hits: print('%-42s %s'%(f,', '.join(hits)))
