from pathlib import Path
import pefile, struct, re
files=[Path('COD OL/codoMP_client_shipRetail.exe'),Path('COD OL/codoMP_client_shipRetailBase.dll'),Path('WeGame/tgp_daemon.exe'),Path('COD OL/TCLS/Client.exe')]
terms=[b'WIN_NO_TCLS',b'IsTCLSLogOn',b'${CODO_TCLS_ZONE}',b'TCLS_SHAREDMEMEMORY',b'TCLS_TASMEMORY_',b'TCLSHOST_MUTEX',b'tcls_core',b'StartFor',b'AddPath',b'cmd_launcher_info.ini',b'client_launcher.exe',b'TCLSClient.dll',b'iGameInitiate']

def ptr_matches(data,val,maxn=100):
    pat=struct.pack('<I',val); out=[]; i=0
    while True:
        j=data.find(pat,i)
        if j<0: return out
        out.append(j); i=j+1
        if len(out)>=maxn:return out

for p in files:
    print('\n'+'='*100);print(p)
    pe=pefile.PE(str(p),fast_load=True); data=p.read_bytes()
    for t in terms:
        hits=[];start=0
        while True:
            i=data.find(t,start)
            if i<0:break
            hits.append(i);start=i+1
        if not hits:continue
        print('TERM',t.decode('ascii','replace'))
        for off in hits[:8]:
            rva=pe.get_rva_from_offset(off); va=pe.OPTIONAL_HEADER.ImageBase+rva
            print(' string off/rva/va',hex(off),hex(rva),hex(va))
            ms=ptr_matches(data,va)
            for m in ms[:30]:
                mr=pe.get_rva_from_offset(m)
                print('   ptr raw/rva/va',hex(m),hex(mr),hex(pe.OPTIONAL_HEADER.ImageBase+mr))
