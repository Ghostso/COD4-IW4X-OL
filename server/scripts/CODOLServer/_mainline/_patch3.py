p="_dyn_game.py"
s=open(p,encoding="utf-8").read()
anchor = "k32 = ctypes.windll.kernel32\npsapi = ctypes.windll.psapi\n"
assert anchor in s
proto = anchor + """
# --- proper 64-bit prototypes (missing these truncates handles) ---
k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                               wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                               ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.CloseHandle.argtypes = [wt.HANDLE]
psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
psapi.EnumProcessModules.restype = wt.BOOL
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.LPWSTR, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD
"""
s=s.replace(anchor, proto)
# use QUERY|VM_READ like the working tool
s=s.replace("h=k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)", "h=k32.OpenProcess(0x0400|0x0010, False, pid)")
s=s.replace('PROCESS_ALL_ACCESS', 'PROCESS_QUERY_INFORMATION|PROCESS_VM_READ')
open(p,"w",encoding="utf-8").write(s)
print("patched")
