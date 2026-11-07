import ctypes, struct, sys
from ctypes import wintypes

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

pid = 9656
h = k32.OpenProcess(0x1F0FFF, False, pid)
if not h:
    print("OpenProcess failed:", k32.GetLastError())
    sys.exit(1)

hMods = (wintypes.HMODULE * 1024)()
cbNeeded = wintypes.DWORD()
LIST_MODULES_32BIT = 0x01

if psapi.EnumProcessModulesEx(h, hMods, ctypes.sizeof(hMods), ctypes.byref(cbNeeded), LIST_MODULES_32BIT):
    n = cbNeeded.value // ctypes.sizeof(wintypes.HMODULE)
    print("Total 32-bit modules:", n)
    for i in range(min(n, 15)):
        mod_name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(h, hMods[i], mod_name, 260)
        base = hMods[i]
        print("  0x%08X : %s" % (base, mod_name.value))
else:
    print("EnumProcessModulesEx failed:", k32.GetLastError())
