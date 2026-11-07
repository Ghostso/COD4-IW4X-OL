
import pefile, hashlib, os
paths={
 'original':r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe',
 'recovered':r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
}
out=[]
for name,p in paths.items():
    d=open(p,'rb').read(); pe=pefile.PE(data=d,fast_load=True)
    out.append('===== %s =====' % name)
    out.append('path=%s' % p)
    out.append('size=%d sha256=%s' % (len(d),hashlib.sha256(d).hexdigest()))
    out.append('machine=%#x subsystem=%#x timestamp=%#x imagebase=%#x entry=%#x sizeofimage=%#x headers=%#x align_file=%#x align_sect=%#x' % (
        pe.FILE_HEADER.Machine, pe.OPTIONAL_HEADER.Subsystem, pe.FILE_HEADER.TimeDateStamp,
        pe.OPTIONAL_HEADER.ImageBase, pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        pe.OPTIONAL_HEADER.SizeOfImage, pe.OPTIONAL_HEADER.SizeOfHeaders,
        pe.OPTIONAL_HEADER.FileAlignment, pe.OPTIONAL_HEADER.SectionAlignment))
    out.append('sections=%d checksum=%#x dllchar=%#x numdirs=%d' % (pe.FILE_HEADER.NumberOfSections,pe.OPTIONAL_HEADER.CheckSum,pe.OPTIONAL_HEADER.DllCharacteristics,pe.OPTIONAL_HEADER.NumberOfRvaAndSizes))
    for s in pe.sections:
        nm=s.Name.rstrip(b'\0').decode('latin1')
        raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
        nz=sum(1 for b in raw if b!=0)
        out.append('SEC %-8s va=%#x vsz=%#x rawptr=%#x rawsz=%#x flags=%#x data_sha=%s nonzero=%d/%d' % (
            nm,s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,s.Characteristics,
            hashlib.sha256(raw).hexdigest() if raw else '-',nz,len(raw)))
    maxend=max((s.PointerToRawData+s.SizeOfRawData) for s in pe.sections)
    out.append('MAX_RAW_END=%#x file_size=%#x overlay=%#x' % (maxend,len(d),len(d)-maxend))
    out.append('')
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_pe_audit.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
d=open(paths['recovered'],'rb').read(); pe=pefile.PE(data=d,fast_load=True)
out2=[]
for s in pe.sections:
    nm=s.Name.rstrip(b'\0').decode('latin1')
    raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    for val,label in ((0,'ZERO'),(0xCC,'CC')):
        best=cur=0;pos=0;bestpos=0
        for i,b in enumerate(raw):
            if b==val:
                if cur==0: pos=i
                cur+=1
                if cur>best: best=cur;bestpos=pos
            else: cur=0
        out2.append('%s %s longest=%#x at_raw_off=%#x pct=%.3f' % (nm,label,best,s.PointerToRawData+bestpos,100.0*sum(1 for b in raw if b==val)/max(1,len(raw))))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_fill_runs.txt','w',encoding='utf-8').write('\n'.join(out2))
print('\n'.join(out2))
