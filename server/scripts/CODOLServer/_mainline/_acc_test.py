import ctypes, ctypes.wintypes as wt, json
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes=[wt.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
import subprocess
out = subprocess.run(["tasklist","/FI","IMAGENAME eq codoMP_client_shipRetail.exe","/FO","CSV","/NH"],capture_output=True,text=True).stdout
pid = int(out.split(",")[1].strip().strip('"'))
# 尝试多种访问权限
for name, acc in [("QUERY_INFO|VM_READ",0x0410), ("ALL_ACCESS",0x1F0FFF), ("VM_READ only",0x0010)]:
    h = k32.OpenProcess(acc, False, pid)
    e = ctypes.get_last_error()
    if h:
        buf = ctypes.create_string_buffer(16); got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x00400000), buf, 16, ctypes.byref(got))
        print("%-20s handle=0x%X read=%s err=%d" % (name, h, ok, ctypes.get_last_error()))
        k32.CloseHandle(h)
    else:
        print("%-20s OpenProcess FAILED err=%d" % (name, e))
