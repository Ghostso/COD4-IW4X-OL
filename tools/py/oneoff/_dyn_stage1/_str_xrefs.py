from pathlib import Path
import pefile,struct
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
cases=[
 (root/r"COD OL\codoMP_client_shipRetailBase.dll",[b"TCLS_SHAREDMEMEMORY",b"TCLS_TASMEMORY_",b"TP3GameGuardShareMapping",b"TPUSERACCOUNT_SHAREDMEMEMORY",b"tcls_core",b"IsTCLSLogOn"]),
 (root/r"COD OL\codoMP_client_shipRetail.exe",[b"IsTCLSLogOn",b"WIN_NO_TCLS",b"TenProxy"]),
 (root/r"WeGame\tcls\tcls_core.exe",[b"TCLS_SHAREDMEMEMORY",b"TCLS_TASMEMORY_",b"tcls_core",b"TCLS_TENPROXY_RESULT",b"TCLS_GMAE_EXIT",b"GetGameSignatrue",b"GetJumpSignatrue"]),
 (root/r"COD OL\TenProxy.dll",[b"TCLS_SHAREDMEMEMORY",b"TCLS_TENPROXY_RESULT",b"TCLS_GMAE_EXIT",b"GetGameSignatrue",b"GetJumpSignatrue"]),
]
for p,terms in cases:
 d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 print("\nFILE",p,"base",hex(base))
 secs=[]
 for s in pe.sections:
  if s.Name.rstrip(b"\0")==b".tvm0": continue
  try: secs.append((s.Name.rstrip(b"\0").decode("latin1"),s.get_data(),base+s.VirtualAddress))
  except Exception as e: pass
 for t in terms:
  offs=[];q=0
  while True:
   i=d.find(t,q)
   if i<0:break
   offs.append(i);q=i+1
  print("TERM",t,"offs",[hex(x) for x in offs])
  for o in offs:
   try: rv=base+pe.get_rva_from_offset(o)
   except Exception as e: print(" mapfail",e);continue
   print(" STR VA",hex(rv),rv)
   hits=[]
   q=0
   while True:
    i=d.find(struct.pack("<I",rv),q)
    if i<0:break
    try: av=base+pe.get_rva_from_offset(i)
    except: q=i+1;continue
    hits.append(av);q=i+1
   print(" REFS",[hex(x) for x in hits])
   for av in hits:
    print("  XREF",hex(av))
    # disasm backwards 64 and forward 160 aligned only roughly
    for name,code,cva in secs:
     if cva<=av<cva+len(code):
      o2=av-cva
      lo=max(0,o2-80);hi=min(len(code),o2+160)
      md=Cs(CS_ARCH_X86,CS_MODE_32)
      for ins in md.disasm(code[lo:hi],cva+lo):
       print((" >>" if ins.address==av else "   "),hex(ins.address),ins.bytes.hex(),ins.mnemonic,ins.op_str)
      break
