import ctypes, ctypes.wintypes as wt
import sys, csv, io, subprocess

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD)
    ]

res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
pids = [int(row[1]) for row in csv.reader(io.StringIO(res.stdout)) if len(row) >= 2 and "codoMP" in row[0]]
if not pids:
    print("codoMP not running")
    sys.exit(1)

pid = pids[0]
# Use exact rights: PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
if not h:
    print(f"OpenProcess failed: {ctypes.get_last_error()}")
    sys.exit(1)

mbi = MEMORY_BASIC_INFORMATION()
addrs = [0x400000, 0x41CB40, 0x4FEA20, 0x74EF10, 0xBA6000]

buf = ctypes.create_string_buffer(32)
read = ctypes.c_size_t(0)

print(f"Testing PID {pid}:")
for addr in addrs:
    if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        prot = hex(mbi.Protect)
        state = hex(mbi.State)
        alloc_prot = hex(mbi.AllocationProtect)
        can_read = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, 16, ctypes.byref(read))
        data_str = bytes(buf.raw[:read.value]).hex() if can_read else f"RPM_ERR_{ctypes.get_last_error()}"
        print(f"  0x{addr:08X}: State={state} Protect={prot} AllocProtect={alloc_prot} Data={data_str}")
    else:
        print(f"  0x{addr:08X}: VirtualQueryEx failed ({ctypes.get_last_error()})")

k32.CloseHandle(h)
