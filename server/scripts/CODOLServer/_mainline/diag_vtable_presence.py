"""诊断: 确认 0x00DE07A4 是否存在于运行中进程, 并放宽实例搜索条件。

三件事:
 1. 读 0x00DE07A4 处的 4 字节, 确认它是不是 vtable 内容(应指向 0x7F0A00 等)
 2. 统计各类型区域数量(MEM_PRIVATE / MEM_MAPPED / MEM_IMAGE)
 3. 不限类型地找 "0x00DE07A4" dword 出现处
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD),
                ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


class PE32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL


def rpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None


def pids():
    sh = k32.CreateToolhelp32Snapshot(2, 0)
    e = PE32W()
    e.dwSize = ctypes.sizeof(e)
    out = []
    ok = k32.Process32FirstW(sh, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == 'codomp_client_shipretail.exe':
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(sh, ctypes.byref(e))
    k32.CloseHandle(sh)
    return out


p = pids()
if not p:
    print('no client')
    raise SystemExit(1)
h = k32.OpenProcess(0x0410, False, p[0])
print('pid=%d handle=0x%X' % (p[0], h))

print()
print('=== 1. 读 0x00DE07A4 (vtable 内容应为 0x007F0A00) ===')
d = rpm(h, 0x00DE07A4, 16)
print('  read =', d.hex() if d else 'FAILED')
if d and len(d) >= 4:
    print('  第一个指针 = 0x%08X' % struct.unpack_from('<I', d, 0)[0])

print()
print('=== 2. 区域类型统计 ===')
counts = {0x20000: 0, 0x40000: 0, 0x1000000: 0, 'other': 0}
sizes = {0x20000: 0, 0x40000: 0, 0x1000000: 0, 'other': 0}
va = 0x10000
mbi = MBI()
while va < 0x7FFF0000:
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(va), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    size = int(mbi.RegionSize) or 0x1000
    if mbi.State == 0x1000:
        t = mbi.Type if mbi.Type in counts else 'other'
        counts[t] += 1
        sizes[t] += size
    va = int(mbi.BaseAddress) + size
for k in counts:
    print('  type=0x%-8X regions=%6d  bytes=%d MB'
          % (k if isinstance(k, int) else 0, counts[k], sizes[k] >> 20))

print()
print('=== 3. 不限类型找 0x00DE07A4 (只扫前 2000 个区, 跳过 >64MB) ===')
needle = struct.pack('<I', 0x00DE07A4)
hits = []
va = 0x10000
n = 0
while va < 0x7FFF0000 and n < 2000 and len(hits) < 20:
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(va), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    size = int(mbi.RegionSize) or 0x1000
    base = int(mbi.BaseAddress)
    prot = mbi.Protect
    ok = (mbi.State == 0x1000 and not (prot & 0x100) and
          (prot & (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)))
    if ok:
        n += 1
        if size <= (64 << 20):
            off = 0
            tail = b''
            while off < size:
                m = min(1 << 20, size - off)
                data = rpm(h, base + off, m)
                if data:
                    blob = tail + data
                    i = blob.find(needle)
                    while i >= 0:
                        a = base + off - len(tail) + i
                        if a % 4 == 0:
                            hits.append((a, mbi.Type))
                        i = blob.find(needle, i + 1)
                    tail = data[-4:]
                off += m
    va = base + size
print('  扫描 %d 区, 命中 %d 处' % (n, len(hits)))
for a, t in hits[:20]:
    print('    0x%08X  type=0x%X' % (a, t))
k32.CloseHandle(h)
