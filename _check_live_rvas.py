import ctypes, ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_ALL_ACCESS = 0x1F0FFF

# Find codoMP_client_shipRetail PID
import csv, io, subprocess
res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
pids = []
for row in csv.reader(io.StringIO(res.stdout)):
    if len(row) >= 2 and "codoMP" in row[0]:
        pids.append(int(row[1]))

print(f"Found codoMP PIDs: {pids}")
if not pids:
    sys.exit(1)

pid = pids[0]
h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
if not h:
    print(f"OpenProcess failed: {ctypes.get_last_error()}")
    sys.exit(1)

# Get module base
hMods = (wt.HMODULE * 1024)()
cbNeeded = wt.DWORD()
base = 0x400000
if psapi.EnumProcessModules(h, hMods, ctypes.sizeof(hMods), ctypes.byref(cbNeeded)):
    base = hMods[0]
print(f"Process {pid} module base: 0x{base:X}")

rvas = {
    "SV_LinkEntity": 0x34EF10,
    "Com_Frame": 0x0FEA20,
    "PmoveSingle": 0x01CB40,
    "SV_Trace": 0x06E780,
    "LevelZoneLoad": 0x09E600,
    "DB_FindXAssetHeader": 0x09CF30,
    "Trace": 0x06EA60,
    "WorldTrace": 0x268220,
    "CollisionMapLoad": 0x262D90,
}

expected_prefixes = {
    "SV_LinkEntity": bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x48]),
    "Com_Frame": bytes([0x55, 0x8B, 0xEC, 0x56, 0x57]),
    "PmoveSingle": bytes([0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x64, 0x01, 0x00, 0x00]),
    "SV_Trace": bytes([0x55, 0x8B, 0xEC, 0x8B, 0x45, 0x1C, 0x8B, 0x4D, 0x18]),
    "LevelZoneLoad": bytes([0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x28, 0x0E, 0x00, 0x00]),
    "DB_FindXAssetHeader": bytes([0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8]),
}

buf = ctypes.create_string_buffer(32)
read = ctypes.c_size_t(0)

print("\n--- Live Memory Byte Checks ---")
for name, rva in rvas.items():
    va = base + rva
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, 16, ctypes.byref(read)):
        live = bytes(buf.raw[:read.value])
        exp = expected_prefixes.get(name)
        if exp:
            match = "EXACT MATCH OK" if live.startswith(exp) else f"MISMATCH (exp {exp.hex()})"
        else:
            match = "INFO"
        print(f"  {name:20} @ 0x{va:08X} (RVA 0x{rva:06X}): {live[:8].hex()} -> {match}")
    else:
        print(f"  {name:20} @ 0x{va:08X}: ReadProcessMemory failed ({ctypes.get_last_error()})")

k32.CloseHandle(h)
