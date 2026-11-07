
import pefile,hashlib,struct,math,os
orig=r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe'
rec=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
do=open(orig,'rb').read(); dr=open(rec,'rb').read(); po=pefile.PE(data=do,fast_load=True); pr=pefile.PE(data=dr,fast_load=True)
out=[]
def raw(pe,d,s):
    return d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData], d[s.PointerToRawData:s.PointerToRawData+min(s.SizeOfRawData,s.Misc_VirtualSize)]
def equal_ratio(a,b):
    n=min(len(a),len(b)); eq=sum(1 for i in range(n) if a[i]==b[i]); return eq,n,(100.0*eq/n if n else 0)
def longest_equal(a,b):
    n=min(len(a),len(b)); best=cur=0; pos=0; bestpos=0
    for i in range(n):
        if a[i]==b[i]:
            if cur==0:pos=i
            cur+=1
            if cur>best:best=cur;bestpos=pos
        else:cur=0
    return best,bestpos
# match sections by virtual address
omap={s.VirtualAddress:s for s in po.sections}; rmap={s.VirtualAddress:s for s in pr.sections}
out.append('SECTION MATCH BY VA')
allva=sorted(set(omap)|set(rmap))
for va in allva:
    os_=omap.get(va); rs_=rmap.get(va)
    on=os_.Name.rstrip(b'\0').decode('latin1') if os_ else '-'; rn=rs_.Name.rstrip(b'\0').decode('latin1') if rs_ else '-'
    out.append('VA %#x original=%s vsz=%#x raw=%#x | recovered=%s vsz=%#x raw=%#x' % (va,on,os_.Misc_VirtualSize if os_ else 0,os_.SizeOfRawData if os_ else 0,rn,rs_.Misc_VirtualSize if rs_ else 0,rs_.SizeOfRawData if rs_ else 0))
    if os_ and rs_:
        a,_=raw(po,do,os_); b,_=raw(pr,dr,rs_)
        eq,n,pct=equal_ratio(a,b); best,bp=longest_equal(a,b)
        out.append('   equal=%d/%d %.3f%% longest=%#x at_raw=%#x' % (eq,n,pct,best,bp))
out.append('')
# directories
for nm,pe,d in [('original',po,do),('recovered',pr,dr)]:
    out.append('===== %s directories =====' % nm)
    for i,e in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
        if e.VirtualAddress or e.Size:
            out.append('DIR[%d] rva=%#x size=%#x' % (i,e.VirtualAddress,e.Size))
    try:
        imps=[]
        for ent in pe.DIRECTORY_ENTRY_IMPORT:
            imps.append(ent.dll.decode('latin1')+':'+','.join((x.name.decode('latin1') if x.name else '#'+str(x.ordinal)) for x in ent.imports))
        out.append('IMPORTS '+repr(imps))
    except Exception as e: out.append('IMPORTS ERROR '+repr(e))
    out.append('')
# known RVA byte presence in original
patterns={}
for rva,nm in [(0xA2E50,'A2E50'),(0xA2D90,'A2D90'),(0x1AC1D0,'CORE_READ'),(0x1ACB00,'CORE_COPY')]:
    b=dr[pr.get_offset_from_rva(rva):pr.get_offset_from_rva(rva)+32]
    patterns[nm]=b
    out.append('%s recovered bytes %s found_in_original_raw=%s' % (nm,b.hex(),do.find(b)>=0))
out.append('')
# large exact match blocks between recovered .text and original sections (bounded)
rsec=next(s for s in pr.sections if s.Name.rstrip(b'\0')==b'.text'); rb=dr[rsec.PointerToRawData:rsec.PointerToRawData+rsec.SizeOfRawData]
out.append('TEXT exact 64-byte blocks present in original:')
for off in range(0,len(rb)-64,0x4000):
    block=rb[off:off+64]
    if block.count(0)!=64 and do.find(block)>=0:
        out.append(' off=%#x rva=%#x block=%s' % (off,rsec.VirtualAddress+off,block.hex()))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_section_compare.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
