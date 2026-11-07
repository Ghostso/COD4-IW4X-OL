import sys, pathlib, shutil, importlib.util
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
print('TOOLS')
for n in ['wpr.exe','xperf.exe','logman.exe','tracelog.exe','tracerpt.exe','wevtutil.exe','netsh.exe','tasklist.exe','wmic.exe','powershell.exe','python.exe','dumpbin.exe','link.exe','cdb.exe','windbg.exe','x64dbg.exe','procmon.exe','procexp.exe','handle.exe','listdlls.exe','tcpview.exe']:
 print(n, shutil.which(n))
print('PYMODULES')
for n in ['frida','psutil','pywintrace','win32api','win32evtlog','etw','yara','pefile','capstone']:
 try: ok=importlib.util.find_spec(n) is not None
 except Exception: ok=False
 print(n,ok)
print('LOGDIRS')
for d in [pathlib.Path('日志'),pathlib.Path('COD OL/Logs'),pathlib.Path('COD OL/TenproxyLog'),pathlib.Path('COD OL/TimeLog'),pathlib.Path('工具')]:
 print('\n==',d,'exists',d.exists(),'==')
 if d.exists():
  for x in sorted(d.rglob('*'),key=lambda p:str(p).lower()):
   if x.is_file():
    try: print(x, x.stat().st_size)
    except OSError: pass
