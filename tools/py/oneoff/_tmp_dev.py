import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=90):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 开发者/控制台相关关键字扫描 (EXE 映像内) ===')
keys=[b'developer', b'developer_script', b'cheats', b'sv_cheats', b'con_con', b'console',
      b'DVAR_CHEAT', b'Cmd_AddCommand', b'Cbuf_AddText', b'com_developer']
for k in keys:
    hits=[]
    i=img.find(k,0)
    while i>=0 and len(hits)<5:
        va=LO+i
        if 0x400000<=va<0x0EA59000 and all(cov[i+j]==1 for j in range(len(k))):
            s=cstr(va,80)
            hits.append((va,s))
        i=img.find(k,i+1)
    print('  %-18s %s' % (k.decode(), [ (hex(a),s) for a,s in hits[:4] ] or '无'))
