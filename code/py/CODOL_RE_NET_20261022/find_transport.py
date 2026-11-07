import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
def find(s):
    b=s.encode(); out=[]; i=0
    while True:
        i=d.find(b,i)
        if i<0: break
        out.append(BASE+i); i+=1
    return out
for s in ['VSDDrvDll.dll','CreateVSDIDrvObj','GameRpcs.dll','TenRpcs.dll','TenProxy.dll','ace-ats32.dll','TCLS_SHAREDMEMORY']:
    locs=find(s)
    print('\n%-22s count=%d %s'%(s,len(locs),[hex(x) for x in locs[:10]]))
    for va in locs[:6]:
        pat=struct.pack('<I',va); hits=[]; i=0
        while True:
            i=d.find(pat,i)
            if i<0: break
            if 0x401000<=BASE+i<0xE5C8000: hits.append(BASE+i)
            i+=1
        if hits: print('    xrefs:',[hex(x) for x in hits[:8]])
