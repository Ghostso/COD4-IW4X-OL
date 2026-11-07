import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 搜 dvar 下行相关关键字 ===')
keys=[b'setclientdvar', b'clientdvar', b'dvars', b'sv_dvars', b'configstring',
      b'CS_DVARS', b'dvar_restrict', b'serverdvar', b'Dvar_RegisterServer',
      b'net_dvar', b'dvar_set']
for k in keys:
    hits=[]
    i=img.find(k,0)
    while i>=0 and len(hits)<4:
        va=LO+i
        if 0x400000<=va<0x0EA59000 and all(cov[i+j]==1 for j in range(len(k))):
            s=cstr(va,90)
            hits.append((hex(va),s))
        i=img.find(k,i+1)
    print('  %-22s %s' % (k.decode(), hits or '无'))
