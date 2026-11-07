from pathlib import Path
import pefile,struct,json
root=Path(r"D:\\BaiduNetdiskDownload\\使命召唤OL")
paths=[root/r"WeGame\\tgp_daemon.exe",root/r"WeGame\\tcls\\tcls_core.exe",root/r"COD OL\\WeGameLauncher\\launcher.exe"]
terms=[b"StartFor",b"AddPath",b"cmd_start_for.ini",b"cmd_launcher_info.ini",b"TCLS_SHAREDMEMEMORY",b"TCLS_TASMEMORY_",b"TP3GameGuardShareMapping",b"TPUSERACCOUNT_SHAREDMEMEMORY",b"codoMP_client_shipRetail.exe",b"tgp_daemon.exe",b"game_id=",b"launcher_ver=",b"StartGame",b"LaunchGame",b"RunGame"]
for p in paths:
 d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 print("FILE",p.name,"base",hex(base),"entry",hex(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint),"size",len(d))
 for t in terms:
  offs=[];q=0
  while True:
   i=d.find(t,q)
   if i<0:break
   offs.append(i);q=i+1
  if not offs: continue
  print(" TERM",t.decode("latin1"))
  for o in offs:
   try: rva=pe.get_rva_from_offset(o); va=base+rva
   except Exception: continue
   print("  STR raw=%#x rva=%#x va=%#x"%(o,rva,va))
   q=0
   while True:
    i=d.find(struct.pack("<I",va),q)
    if i<0:break
    try: x=base+pe.get_rva_from_offset(i)
    except Exception:q=i+1;continue
    print("   ABSREF",hex(x));q=i+1
