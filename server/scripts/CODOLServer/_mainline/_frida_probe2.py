import frida, time, sys
exe=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe"
cwd=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923"
d=frida.get_local_device()
print("spawning",flush=True)
p=d.spawn([exe],cwd=cwd)
print("spawned pid",p,flush=True)
t0=time.time()
try:
    s=d.attach(p)
    print("attached after",round(time.time()-t0,2),flush=True)
except Exception as e:
    print("attach FAILED after",round(time.time()-t0,2),repr(e),flush=True)
    sys.exit(1)
try:
    sc=s.create_script("send({k:'loaded'});")
    sc.on('message',lambda m,d: print('MSG',m,flush=True))
    sc.load()
    print("script loaded",flush=True)
except Exception as e:
    print("script load failed",repr(e),flush=True)
try: d.kill(p)
except Exception: pass
