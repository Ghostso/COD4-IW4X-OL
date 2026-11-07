
import ctypes, os, sys
print("cwd:", os.getcwd())
print("exe:", sys.executable)
try:
    admin = ctypes.windll.shell32.IsUserAnAdmin()
except Exception as e:
    admin = "err"
print("IsUserAnAdmin:", admin)
# try writing to System32
p = os.path.join(os.environ["windir"], "System32", "_z7_writetest.txt")
try:
    open(p, "w").write("x")
    os.remove(p)
    print("System32 write: OK")
except Exception as e:
    print("System32 write: FAIL", e)
# try opening hosts for append
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")
try:
    f = open(H, "a"); f.close()
    print("hosts append-open: OK")
except Exception as e:
    print("hosts append-open: FAIL", e)
