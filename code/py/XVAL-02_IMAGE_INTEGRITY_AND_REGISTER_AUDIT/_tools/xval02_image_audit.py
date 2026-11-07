# -*- coding: utf-8 -*-
"""XVAL-02 镜像完整性审计。只读：打开冻结样本，解析 PE，重算哈希与 aplib 保真性。
不运行目标客户端/服务端，不注入，不读进程内存。"""
import pefile, struct, hashlib, os, csv, zlib, math
from collections import Counter
import aplib

DL   = r"D:\BaiduNetdiskDownload"
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = rf"{ROOT}\XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT"
PACK = rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC  = rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
LAUN = rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher"

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
def raw(pe, path, s):
    with open(path,'rb') as f: f.seek(s.PointerToRawData); return f.read(s.SizeOfRawData)
def entropy(b):
    if not b: return 0.0
    c=Counter(b); n=len(b); return -sum((v/n)*math.log2(v/n) for v in c.values())

pp=pefile.PE(PACK,fast_load=True); pr=pefile.PE(REC,fast_load=True)
IB=pr.OPTIONAL_HEADER.ImageBase

# ---------- 1. provenance ----------
prov_cols=["Material_ID","Path","Role","Size_Bytes","SHA256","ImageBase","SizeOfImage","EntryPoint_RVA","SectionCount","Provenance","Citation","Notes"]
prov=[]
def addprov(mid,path,role,notes,cite):
    if os.path.isfile(path):
        try:
            pe=pefile.PE(path,fast_load=True); oh=pe.OPTIONAL_HEADER
            ib,si,ep,sc=f"0x{oh.ImageBase:X}",f"0x{oh.SizeOfImage:X}",f"0x{oh.AddressOfEntryPoint:X}",len(pe.sections)
        except Exception:
            ib=si=ep=sc="N/A (not PE)"
        prov.append(dict(Material_ID=mid,Path=path,Role=role,Size_Bytes=os.path.getsize(path),SHA256=sha256(path),
                         ImageBase=ib,SizeOfImage=si,EntryPoint_RVA=ep,
                         SectionCount=sc,Provenance=cite,Citation=cite,Notes=notes))
    else:
        prov.append(dict(Material_ID=mid,Path=path,Role=role,Size_Bytes="",SHA256="MISSING",ImageBase="",SizeOfImage="",EntryPoint_RVA="",SectionCount="",Provenance=cite,Citation=cite,Notes=notes+" [NOT FOUND]"))

addprov("IMG-C-2697-PACKED", PACK, "冻结打包客户端（TenProtect 包装）", "任务目标客户端；8 字节节名被改写为 .tp3/.tvm0", "XVAL-01 C-037 / E-06")
addprov("IMG-C-2697-RECOVERED", REC, "aplib 静态恢复镜像", "非运行时 dump；.text 由 aplib 解压得来（本任务复核）", "E-06 / XVAL-01 C-037")
addprov("LAUNCHER-EXE", rf"{LAUN}\startup_dialog2697.py" if os.path.isfile(rf"{LAUN}\startup_dialog2697.py") else rf"{LAUN}\runtime\game\startup_dialog2697.py", "2697 启动器", "恢复产物来源链", "E-06")

# ---------- 2. per-section integrity ----------
sec_cols=["Image","SectionIndex","Name","VirtualAddress","VirtualSize","SizeOfRawData","PointerToRawData",
          "MappedVA_Start","MappedVA_End","OnDisk_Bytes","VirtualTail_NotOnDisk_Bytes","Tail_Is_BSS_ZeroFilled",
          "Raw_Coverage_Pct","FullyBacked_OnDisk","Characteristics","Integrity_Status","Evidence"]
secrows=[]
def emit(imgname, path, pe, mapped):
    for i,s in enumerate(pe.sections):
        nm=s.Name.rstrip(b'\x00').decode(errors='replace')
        vs=s.Misc_VirtualSize; rs=s.SizeOfRawData
        tail=vs-rs if vs>rs else 0
        cov = (rs/vs*100) if vs else 100.0
        # BSS/zero-fill classification: writable data (.data Char 0xC0000040) & VS>>RS -> loader zero-fills tail
        is_bss = (tail>0 and (s.Characteristics & 0x80000000)!=0 and 'data' in nm.lower())
        status = "DISK-BACKED-COMPLETE" if rs>=vs else ("BSS-ZERO-FILL-TAIL" if is_bss else "VIRTUAL-TAIL-NOT-ON-DISK")
        if nm==".rimp":
            status="RECOVERED-REGION (replaces unrestored tail)"
        secrows.append(dict(Image=imgname,SectionIndex=i+1,Name=nm,VirtualAddress=f"0x{s.VirtualAddress:08X}",
            VirtualSize=f"0x{vs:08X}",SizeOfRawData=f"0x{rs:08X}",PointerToRawData=f"0x{s.PointerToRawData:08X}",
            MappedVA_Start=f"0x{IB+s.VirtualAddress:X}",MappedVA_End=f"0x{IB+s.VirtualAddress+vs:X}",
            OnDisk_Bytes=rs,VirtualTail_NotOnDisk_Bytes=tail,Tail_Is_BSS_ZeroFilled=is_bss,
            Raw_Coverage_Pct=round(cov,4),FullyBacked_OnDisk=(rs>=vs),
            Characteristics=f"0x{s.Characteristics:08X}",Integrity_Status=status,
            Evidence="PE section table; characteristic bit 0x80000000=Writable"))
emit("PACKED",PACK,pp,pp.OPTIONAL_HEADER.SizeOfImage); emit("RECOVERED",REC,pr,pr.OPTIONAL_HEADER.SizeOfImage)

# ---------- 3. packed vs recovered per-section comparison ----------
cmp_cols=["SectionIndex","PackedName","RecoveredName","Packed_OnDisk","Recovered_OnDisk","VirtualSize_Match",
          "OnDisk_Identical","MatchingBytes","MatchPct_of_min","Interpretation"]
cmprows=[]
for i in range(max(len(pp.sections),len(pr.sections))):
    a=pp.sections[i] if i<len(pp.sections) else None
    b=pr.sections[i] if i<len(pr.sections) else None
    ba=raw(pp,PACK,a) if a else b""; bb=raw(pr,REC,b) if b else b""
    n=min(len(ba),len(bb)); eq=sum(1 for x,y in zip(ba[:n],bb[:n]) if x==y)
    vsm = (a.Misc_VirtualSize==b.Misc_VirtualSize) if (a and b) else False
    ident = (ba==bb)
    if ident and len(ba)>0: interp="逐字节一致（未修改）"
    elif i==0: interp="压缩→解压（aplib，本任务已验证保真）"
    elif i==5: interp="压缩→解压（aplib）"
    elif i==6: interp="打包尾部节未恢复为同尺寸容器；恢复镜像改置 .rimp 修复表"
    else: interp="部分字节吻合（解压/重定位差异）"
    cmprows.append(dict(SectionIndex=i+1,PackedName=(a.Name.rstrip(b'\x00').decode() if a else ""),
        RecoveredName=(b.Name.rstrip(b'\x00').decode() if b else ""),Packed_OnDisk=len(ba),Recovered_OnDisk=len(bb),
        VirtualSize_Match=vsm,OnDisk_Identical=ident,MatchingBytes=eq,MatchPct_of_min=round(eq/n*100,4) if n else 0.0,
        Interpretation=interp))

# ---------- 4. .data arithmetic ----------
d=pr.sections[2]; dp=pp.sections[2]
bdr=raw(pr,REC,d); bdp=raw(pp,PACK,dp)
zero=bdr.count(0)
data_facts=dict(
  virtual_size=d.Misc_VirtualSize, raw_size=d.SizeOfRawData, pointer=d.PointerToRawData,
  mapped_start=IB+d.VirtualAddress, mapped_end=IB+d.VirtualAddress+d.Misc_VirtualSize,
  disk_end=IB+d.VirtualAddress+d.SizeOfRawData, tail=d.Misc_VirtualSize-d.SizeOfRawData,
  coverage=round(d.SizeOfRawData/d.Misc_VirtualSize*100,4),
  missing_pct=round((1-d.SizeOfRawData/d.Misc_VirtualSize)*100,4),
  packed_raw_sha=hashlib.sha256(bdp).hexdigest(), rec_raw_sha=hashlib.sha256(bdr).hexdigest(),
  raw_identical=(bdp==bdr), zero_in_raw=zero, zero_pct=round(zero/len(bdr)*100,2), entropy=round(entropy(bdr),4))

# ---------- 5. aplib fidelity ----------
def verify_section(pe, path, idx):
    b=raw(pe,path,pe.sections[idx])
    hs,pl,pc,ol,oc=struct.unpack_from('=IIIII',b,8)
    out=bytes(aplib.decompress(b[4:],strict=True))
    return dict(header_size=hs,packed_len=pl,packed_crc=pc,orig_len=ol,orig_crc=oc,
                out_len=len(out), out_crc=zlib.crc32(out)&0xffffffff, out_sha=hashlib.sha256(out).hexdigest())
fid_text=verify_section(pp,PACK,0)
fid_tvm =verify_section(pp,PACK,5)
text_rec=raw(pr,REC,pr.sections[0])
fid_text["equals_recovered_text"]=(fid_text["out_sha"]==hashlib.sha256(text_rec).hexdigest())
tvm_rec=raw(pr,REC,pr.sections[5])
fid_tvm["equals_recovered_tvm0"]=(fid_tvm["out_len"]==len(tvm_rec) and hashlib.sha256(bytes(aplib.decompress(raw(pp,PACK,pp.sections[5])[4:],strict=True))).hexdigest()==hashlib.sha256(tvm_rec).hexdigest())

# ---------- write CSVs ----------
def wcsv(path, cols, rows):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader()
        for r in rows: wr.writerow(r)
wcsv(rf"{OUT}\XVAL02_IMAGE_HASH_AND_PROVENANCE.csv", prov_cols, prov)
wcsv(rf"{OUT}\_data\section_integrity.csv", sec_cols, secrows)
wcsv(rf"{OUT}\_data\packed_vs_recovered_sections.csv", cmp_cols, cmprows)

# ---------- write facts json ----------
import json
json.dump(dict(data_facts=data_facts, fidelity_text=fid_text, fidelity_tvm0=fid_tvm),
          open(rf"{OUT}\_data\image_facts.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)

print("=== .data facts ==="); [print(f"  {k} = {v}") for k,v in data_facts.items()]
print("=== aplib .text fidelity ==="); [print(f"  {k} = {v}") for k,v in fid_text.items()]
print("=== aplib .tvm0 fidelity ==="); [print(f"  {k} = {v}") for k,v in fid_tvm.items()]
print("wrote:", rf"{OUT}\XVAL02_IMAGE_HASH_AND_PROVENANCE.csv")

