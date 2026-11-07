import os,re
root=r'COD OL'
keys=[b'GDPOpenProtocol',b'.tdr',b'GDP_CF_',b'Blaze',b'DW_LOBBY',b'dwauth.ini',b'stun.ini']
for dirpath,dirs,files in os.walk(root):
    for f in files:
        p=os.path.join(dirpath,f)
        try:
            if os.path.getsize(p)>90_000_000: continue
            d=open(p,'rb').read()
        except: continue
        hits=[k.decode()+':'+str(d.count(k)) for k in keys if d.count(k)]
        if hits: print('%-60s %s'%(os.path.relpath(p,root),', '.join(hits)))
