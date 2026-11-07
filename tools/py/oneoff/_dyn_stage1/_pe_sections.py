from pathlib import Path
import pefile
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
for rel in [r"WeGame\tgp_daemon.exe",r"WeGame\tcls\tcls_core.exe"]:
 p=root/rel; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 print("=====",rel,"base",hex(base),"entry",hex(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint),"size",len(d))
 for s in pe.sections:
  print("SEC",s.Name.rstrip(b"\0").decode("latin1"),"va",hex(base+s.VirtualAddress),"vsize",hex(s.Misc_VirtualSize),"raw",hex(s.PointerToRawData),"rawsize",hex(s.SizeOfRawData),"exec",hex(s.Characteristics))
 for i,d0 in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
  print("DIR",i,d0.name if hasattr(d0,"name") else "",hex(d0.VirtualAddress),hex(d0.Size))
