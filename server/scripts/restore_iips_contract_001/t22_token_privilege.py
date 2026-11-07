"""RESTORE-IIPS-CONTRACT-001 / Task 18 - is SeCreateGlobalPrivilege available?

The contract interval between "window created" and "LoadLibrary IFS.dll" contains
SetPrivilege / IIPSWERR_PRIVILEGE_SE_CREATE_GLOBAL_NAME, and the later steps need
Global\ named objects. So the token privilege state is the most concrete candidate
for the unmet precondition.

This is a plain token query (GetTokenInformation). It changes nothing.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")

advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

TOKEN_QUERY = 0x0008
TokenPrivileges = 3
SE_PRIVILEGE_ENABLED = 0x00000002


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wt.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 64)]


INTERESTING = [
    "SeCreateGlobalPrivilege",
    "SeDebugPrivilege",
    "SeShutdownPrivilege",
    "SeTcbPrivilege",
    "SeAssignPrimaryTokenPrivilege",
    "SeIncreaseQuotaPrivilege",
    "SeChangeNotifyPrivilege",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 18: token privilege state ===")
    print()

    # GetCurrentProcess returns the pseudo-handle -1; declare the argtypes so
    # ctypes does not truncate/mangle it (err=6 here was ERROR_INVALID_HANDLE
    # caused by the untyped call, not by a real privilege problem).
    kernel32.GetCurrentProcess.restype = wt.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    advapi32.OpenProcessToken.restype = wt.BOOL
    advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                          ctypes.POINTER(wt.HANDLE)]
    advapi32.GetTokenInformation.restype = wt.BOOL
    advapi32.GetTokenInformation.argtypes = [wt.HANDLE, ctypes.c_int,
                                             ctypes.c_void_p, wt.DWORD,
                                             ctypes.POINTER(wt.DWORD)]
    advapi32.LookupPrivilegeNameW.restype = wt.BOOL
    advapi32.LookupPrivilegeNameW.argtypes = [wt.LPCWSTR,
                                              ctypes.POINTER(LUID),
                                              wt.LPWSTR,
                                              ctypes.POINTER(wt.DWORD)]

    tok = wt.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_QUERY,
                                    ctypes.byref(tok)):
        print("  OpenProcessToken failed err=%d" % ctypes.get_last_error())
        return 1

    buf = TOKEN_PRIVILEGES()
    ret = wt.DWORD(0)
    ok = advapi32.GetTokenInformation(tok, TokenPrivileges, ctypes.byref(buf),
                                     ctypes.sizeof(buf), ctypes.byref(ret))
    if not ok:
        print("  GetTokenInformation failed err=%d" % ctypes.get_last_error())
        return 1

    n = buf.PrivilegeCount
    print("  privileges in token: %d" % n)
    rep["privilege_count"] = n

    # Build a map name -> attributes for the privileges we care about.
    found = {}
    for i in range(n):
        luid = buf.Privileges[i].Luid
        size = wt.DWORD(0)
        # First call gets the size via ERROR_INSUFFICIENT_BUFFER.
        advapi32.LookupPrivilegeNameW(None, ctypes.byref(luid), None,
                                     ctypes.byref(size))
        bufname = ctypes.create_unicode_buffer(size.value + 1)
        if advapi32.LookupPrivilegeNameW(None, ctypes.byref(luid), bufname,
                                         ctypes.byref(size)):
            found[bufname.value] = buf.Privileges[i].Attributes

    rep["privileges"] = {k: "0x%X" % v for k, v in sorted(found.items())}
    print()
    for p in INTERESTING:
        if p in found:
            attr = found[p]
            enabled = bool(attr & SE_PRIVILEGE_ENABLED)
            print("  %-32s PRESENT   enabled=%s (attr=0x%X)" % (p, enabled, attr))
            rep.setdefault("interesting", {})[p] = {"present": True,
                                                   "enabled": enabled,
                                                   "attr": "0x%X" % attr}
        else:
            print("  %-32s ABSENT" % p)
            rep.setdefault("interesting", {})[p] = {"present": False}

    # Is the process elevated?
    try:
        admin = ctypes.windll.shell32.IsUserAnAdmin()
        rep["is_admin"] = bool(admin)
        print()
        print("  process elevated (IsUserAnAdmin): %s" % bool(admin))
    except Exception:
        rep["is_admin"] = None

    scg = rep.get("interesting", {}).get("SeCreateGlobalPrivilege", {})
    rep["se_create_global"] = {
        "present": scg.get("present", False),
        "enabled": scg.get("enabled", False),
    }
    print()
    if not scg.get("present"):
        print("  FINDING: SeCreateGlobalPrivilege is NOT present in the token.")
        print("           The contract's SetPrivilege step cannot grant it, and")
        print("           creating/opening Global\\ objects would fail with")
        print("           ERROR_PRIVILEGE_NOT_HELD (1314).")
    elif not scg.get("enabled"):
        print("  FINDING: SeCreateGlobalPrivilege is present but DISABLED.")
        print("           It can be enabled by SetPrivilege; whether the provider")
        print("           does so is a separate question.")
    else:
        print("  FINDING: SeCreateGlobalPrivilege is present and ENABLED, so this")
        print("           is not the unmet precondition.")

    rep["note"] = ("This is a plain token query; it changes nothing. It is a "
                   "CANDIDATE-level datum: it constrains the interval between "
                   "window creation and LoadLibrary(IFS.dll) but does not by "
                   "itself prove the provider's SetPrivilege step failed.")
    with open(os.path.join(OUT, "t22_token_privilege.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t22_token_privilege.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
