
import ctypes,ctypes.wintypes as wt
k32=ctypes.WinDLL("kernel32"); adv=ctypes.WinDLL("advapi32")
h=wt.HANDLE(); adv.OpenProcessToken(k32.GetCurrentProcess(),0x8,ctypes.byref(h))
class TIE(ctypes.Structure):
    _fields_=[("User",ctypes.c_void_p),("Groups",ctypes.c_void_p),("Privileges",ctypes.c_void_p),
              ("AuthenticationId",ctypes.c_void_p),("Type",wt.DWORD),("ImpersonationLevel",wt.DWORD),
              ("DynamicCharged",wt.DWORD),("DynamicAvailable",wt.DWORD),("GroupCount",wt.DWORD),
              ("PrivilegeCount",wt.DWORD),("VariableLength",ctypes.c_void_p)]
ti=TIE(); n=wt.DWORD()
adv.GetTokenInformation(h,1,ctypes.byref(ti),ctypes.sizeof(ti),ctypes.byref(n))
t=ti.User
class SID(ctypes.Structure):
    _fields_=[("Revision",ctypes.c_ubyte),("SubAuthorityCount",ctypes.c_ubyte),
              ("IdentifierAuthority",ctypes.c_ubyte*6),("SubAuthority",wt.DWORD*16)]
s=ctypes.cast(t,ctypes.POINTER(SID)).contents
print("SID rev",s.Revision,"subs",[s.SubAuthority[i] for i in range(s.SubAuthorityCount)])
# integrity level (token info class 25)
lvl=wt.DWORD()
adv.GetTokenInformation(h,25,ctypes.byref(lvl),ctypes.sizeof(lvl),ctypes.byref(n))
print("integrity RID",lvl.value>>12 if lvl.value else lvl.value,"(0x%X)"%lvl.value)
