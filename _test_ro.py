import subprocess, time, os

room_owner = r"E:\CODOL_SANDBOX\RUN001\Ayria\ol_room_owner.exe"
p = subprocess.Popen([room_owner], cwd=r"E:\CODOL_SANDBOX\RUN001", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(2)
print("ol_room_owner running:", p.poll() is None)
p.terminate()
stdout, stderr = p.communicate()
print("STDOUT:", stdout)
print("STDERR:", stderr)
