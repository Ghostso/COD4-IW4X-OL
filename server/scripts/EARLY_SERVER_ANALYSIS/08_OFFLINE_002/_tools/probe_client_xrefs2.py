import pefile, re, struct, json, os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

P=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
OUT=r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\08_OFFLINE_002\_evidence"
os.makedirs(OUT, exist_ok=True)
pe=pefile.PE(P, fast_load=False); IB=pe.OPTIONAL_HEADER.ImageBase
data=open(P,'rb').read()

def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+(rva-s.VirtualAddress)
    return None
def off2rva(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData+s.SizeOfRawData:
            return s.VirtualAddress+(off-s.PointerToRawData)
    return None

report={}
report['file']=P
report['sha256']=__import__('hashlib').sha256(data).hexdigest()
report['size']=len(data)
report['imagebase']=hex(IB)
report['sections']=[{'name':s.Name.rstrip(b'\x00').decode('latin1'),'va':hex(s.VirtualAddress),'vsize':hex(s.Misc_VirtualSize),'rawsize':hex(s.SizeOfRawData),'rawptr':hex(s.PointerToRawData),'chars':hex(s.Characteristics)} for s in pe.sections]

targets={
 'netchan_established':0x8489ac,
 'received_gamestate':0x849238,
 'parse_gamestate_begin':0x849358,
 'parse_gamestate_badcmd':0x849388,
 'parse_gamestate_badclient':0x8493b0,
 'configstrings_percent':0x849210,
 'nonbaseline_snap':0x848f70,
 'cl_getsnapshot_trunc':0x846370,
 'g_find_cs_overflow':0x85d13c,
 'exe_cs_mismatch':0x84933c,
 'exe_awaiting_gs':0x86b724,
 'baseline_lower':0x74e784,
}
strcheck={}
for name,rva in targets.items():
    off=rva2off(rva)
    if off is None:
        strcheck[name]={'rva':hex(rva),'present':False,'reason':'rva not mapped'}
        continue
    chunk=data[off:off+80]
    s=chunk.split(b'\x00')[0].decode('latin1','replace')
    strcheck[name]={'rva':hex(rva),'off':hex(off),'text':s,'present':True}
report['string_check']=strcheck

server_cited={
 'c1_0x49dd7e':0x49dd7e,
 'c1_0x49d9ce':0x49d9ce,
 'c1_sub_5A0510':0x5a0510,
 'cg_parseServerinfo_0x465f57':0x465f57,
 'cg_parseServerinfo_0x465bc1':0x465bc1,
 'cg_parseServerinfo_0x465c27':0x465c27,
}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
cited={}
for name,rva in server_cited.items():
    off=rva2off(rva)
    entry={'rva':hex(rva),'off':hex(off) if off is not None else None}
    if off is not None:
        begin=max(0,off-48); end=min(len(data),off+96)
        ins=[]
        for i in md.disasm(data[begin:end], IB+begin):
            ins.append('%08x %-20s %s %s'%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
        entry['disasm']=ins
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
                entry['section']=s.Name.rstrip(b'\x00').decode('latin1')
    cited[name]=entry
report['server_cited_rvas']=cited

def find_xrefs(srva):
    va=IB+srva
    pat=struct.pack('<I',va)
    hits=[]
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000): continue
        raw=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
        start=0
        while True:
            j=raw.find(pat,start)
            if j<0: break
            hits.append(s.VirtualAddress+j); start=j+1
    return hits
xrefs={}
for name,rva in targets.items():
    xrefs[name]=[hex(x) for x in find_xrefs(rva)]
report['string_xrefs']=xrefs

with open(os.path.join(OUT,'client_xrefs.json'),'w',encoding='utf-8') as f:
    json.dump(report,f,indent=2)

print('sha256',report['sha256'])
print('sections:',[(s['name'],s['va'],s['vsize']) for s in report['sections']])
for k,v in strcheck.items():
    print('STR',k,hex(targets[k]),'->',repr(v.get('text','')[:60]))
print('--- server-cited rvas ---')
for k,v in cited.items():
    print(k,v.get('section'),'off',v.get('off'))
    for line in v.get('disasm',[])[:14]:
        print('   ',line)
print('--- xrefs ---')
for k,v in xrefs.items():
    print(k, v)
