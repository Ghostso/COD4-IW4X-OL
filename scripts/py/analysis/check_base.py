import ctypes, struct, sys
from ctypes import wintypes

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

pid = 9656
h = k32.OpenProcess(0x1F0FFF, False, pid)
if not h:
    print("OpenProcess failed:", k32.GetLastError())
    sys.exit(1)

# EnumProcessModules
hMods = (wintypes.HMODULE * 1024)()
cbNeeded = wintypes.DWORD()

if psapi.EnumProcessModules(h, hMods, ctypes.sizeof(hMods), ctypes.byref(cbNeeded)):
    n = cbNeeded.value // ctypes.sizeof(wintypes.HMODULE)
    print("Total modules:", n)
    for i in range(min(n, 10)):
        mod_name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(h, hMods[i], mod_name, 260)
        base = hMods[i]
        print("  0x%08X : %s" % (base, mod_name.value))
else:
    print("EnumProcessModules failed:", k32.GetLastError())
