
import ctypes,ctypes.wintypes as wt,sys
k32=ctypes.WinDLL("kernel32",use_last_error=True)
pid=int(sys.argv[1])
for acc,name in ((0x0410,"QUERY|VM_READ"),(0x0010,"VM_READ"),(0x0400,"QUERY")):
    h=k32.OpenProcess(acc,False,pid)
    print(name,"OpenProcess ->",h,"err",ctypes.get_last_error() if not h else 0)
    if h:
        buf=ctypes.create_string_buffer(16); got=ctypes.c_size_t(0)
        ok=k32.ReadProcessMemory(h,ctypes.c_void_p(0x400000),buf,16,ctypes.byref(got))
        print("   ReadProcessMemory ok=",ok,"got=",got.value,"err=",ctypes.get_last_error())
        k32.CloseHandle(h)
