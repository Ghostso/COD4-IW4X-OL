from pathlib import Path
import pefile,struct,re
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
for rel in [r"COD OL\codoMP_client_shipRetail.exe",r"COD OL\codoMP_client_shipRetailBase.dll",r"COD OL\TenProxy.dll",r"COD OL\TCLS\Client.exe",r"WeGame\tcls\tcls_core.exe"]:
 p=root/rel
 if not p.exists(): print("MISS",rel); continue
 d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); pe.parse_data_directories()
 print("\nFILE",rel,"base",hex(pe.OPTIONAL_HEADER.ImageBase),"entry",hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
 funcs=[]
 for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
  for imp in e.imports:
   if imp.name:
    n=imp.name.decode("latin1")
    if re.search(r"(OpenFileMapping|CreateFileMapping|MapViewOfFile|GetCommandLine|GetEnvironmentVariable|CreateProcess|ShellExecute|OpenMutex|CreateMutex|GetCurrentProcessId|CreateNamedPipe|WaitNamedPipe|CallNamedPipe|ConnectNamedPipe|RegOpenKey|RegQueryValue|DeviceIoControl)",n,re.I):
     funcs.append((n,imp.address))
 print("WATCHED",funcs)
 # call [iat] and direct pointer refs
 base=pe.OPTIONAL_HEADER.ImageBase; text=next((s for s in pe.sections if s.Name.rstrip(b"\0") in (b".text",b"CODE")),None)
 if text is None: print("NO_TEXT"); continue
 code=text.get_data(); va=base+text.VirtualAddress
 for n,iat in funcs:
  pat=struct.pack("<I",iat)
  refs=[];st=0
  while True:
   i=d.find(pat,st)
   if i<0:break
   try: av=base+pe.get_rva_from_offset(i)
   except: st=i+1;continue
   refs.append(av);st=i+1
  print(" IAT",n,hex(iat),"PTRREFS",[hex(x) for x in refs[:20]])
  md=Cs(CS_ARCH_X86,CS_MODE_32)
  for ins in md.disasm(code,va):
   if ins.mnemonic.startswith("call") and (hex(iat) in ins.op_str or str(iat) in ins.op_str):
    print("  CALL",hex(ins.address),ins.mnemonic,ins.op_str)
