
import ctypes,ctypes.wintypes as wt,subprocess,time
k32=ctypes.WinDLL("kernel32",use_last_error=True)
p=subprocess.Popen(["notepad.exe"]); time.sleep(2)
h=k32.OpenProcess(0x0410,False,p.pid)
buf=ctypes.create_string_buffer(64); got=ctypes.c_size_t(0)
ok=k32.ReadProcessMemory(h,ctypes.c_void_p(0x400000),buf,64,ctypes.byref(got))
print("notepad pid",p.pid,"handle",h,"read_ok",ok,"got",got.value,"err",ctypes.get_last_error())
p.terminate()
