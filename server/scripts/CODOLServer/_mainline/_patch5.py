p="_dyn_game.py"
s=open(p,encoding="utf-8").read()
cp = """k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                               wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                               ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
"""
assert cp in s
s = s.replace(cp, "")   # remove from early block
# re-insert after PROCESS_INFORMATION class definition
anchor = """class PROCESS_INFORMATION(ctypes.Structure):
    _fields_=[("hProcess",wt.HANDLE),("hThread",wt.HANDLE),("dwProcessId",wt.DWORD),("dwThreadId",wt.DWORD)]
"""
assert anchor in s
s = s.replace(anchor, anchor + "\n" + cp)
open(p,"w",encoding="utf-8").write(s)
print("moved")
