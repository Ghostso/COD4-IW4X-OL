
import subprocess, time, os, sys, json, signal
root=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
exe=os.path.join(root,'codoMP_client_shipRetail.exe')
p=subprocess.Popen([exe],cwd=root)
print('pid',p.pid,flush=True)
time.sleep(2)
# enumerate after platform DLLs likely loaded
r=subprocess.run([sys.executable,r'D:\BaiduNetdiskDownload\使命召唤OL\_enum_handles.py',str(p.pid)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
print(r.stdout,flush=True); print('ERR',r.stderr,flush=True)
# leave for a moment then close
p.terminate()
try:p.wait(5)
except: p.kill()
print('rc',p.returncode,flush=True)
