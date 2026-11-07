import frida, time, sys, os
d=frida.get_local_device()
p=d.spawn([r"C:\Windows\System32\notepad.exe"])
print("spawned",p,flush=True)
s=d.attach(p); print("attached",flush=True)
sc=s.create_script("send({k:'hi'});")
sc.on("message", lambda m,d: print("MSG",m,flush=True))
sc.load(); print("loaded",flush=True)
d.resume(p); print("resumed",flush=True)
time.sleep(3)
try: d.kill(p)
except Exception: pass
print("ok",flush=True)
