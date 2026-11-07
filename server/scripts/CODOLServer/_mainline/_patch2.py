p="_dyn_game.py"
s=open(p,encoding="utf-8").read()
old = """def enable_debug():
    adv=ctypes.windll.advapi32
    k32.GetCurrentProcess.restype=wt.HANDLE
    h=wt.HANDLE()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES|TOKEN_QUERY, ctypes.byref(h)):
        return False, ctypes.get_last_error()
    luid=LUID()
    adv.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid))
    tp=TP(); tp.PrivilegeCount=1; tp.Privileges[0].Luid=luid; tp.Privileges[0].Attributes=SE_PRIVILEGE_ENABLED
    r=adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    return bool(r), ctypes.get_last_error()"""
new = """def enable_debug():
    adv=ctypes.WinDLL('advapi32', use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    adv.OpenProcessToken.restype = wt.BOOL
    adv.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, ctypes.POINTER(LUID)]
    adv.LookupPrivilegeValueW.restype = wt.BOOL
    adv.AdjustTokenPrivileges.argtypes = [ctypes.c_void_p, wt.BOOL, ctypes.POINTER(TP), wt.DWORD, ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
    adv.AdjustTokenPrivileges.restype = wt.BOOL
    h = ctypes.c_void_p()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES|TOKEN_QUERY, ctypes.byref(h)):
        return False, ctypes.get_last_error()
    luid=LUID()
    adv.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid))
    tp=TP(); tp.PrivilegeCount=1; tp.Privileges[0].Luid=luid; tp.Privileges[0].Attributes=SE_PRIVILEGE_ENABLED
    r=adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    err=ctypes.get_last_error()
    k32.CloseHandle(h)
    return bool(r), err"""
assert old in s, "pattern not found"
s=s.replace(old,new)
open(p,"w",encoding="utf-8").write(s)
print("patched")
