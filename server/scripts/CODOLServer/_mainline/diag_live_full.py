"""在活进程上做完整诊断（一次跑完，避免跨次状态漂移）。

检查:
  1. 模块枚举（两种快照标志都试）
  2. 主模块基址与大小
  3. 0x400000 处是否 MZ（PE 头）
  4. 0x00DE07A4 是否可读，内容是什么
  5. 若 0x00DE07A4 不可读，扫附近哪些页可读
  6. 全用户空间找 "MZ" 头，确认主模块真实基址
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


class ME32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", wt.WCHAR * 256), ("szExePath", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(ME32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(ME32W)]
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.restype = wt.BOOL


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


def rpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None


p = pids()
if not p:
    print('客户端未运行')
    raise SystemExit(1)
pid = p[0]
h = k32.OpenProcess(0x0410, False, pid)
print('pid=%d handle=0x%X err=%d' % (pid, h, ctypes.get_last_error()))
if not h:
    raise SystemExit(2)

print()
print('=== 1. 模块枚举 (TH32CS_SNAPMODULE|SNAPMODULE32 = 0x18) ===')
sh = k32.CreateToolhelp32Snapshot(0x18, pid)
print('  snapshot=', sh, 'err=', ctypes.get_last_error())
if sh and sh != ctypes.c_void_p(-1).value:
    me = ME32W()
    me.dwSize = ctypes.sizeof(me)
    ok = k32.Module32FirstW(sh, ctypes.byref(me))
    print('  Module32FirstW=', ok, 'err=', ctypes.get_last_error())
    cnt = 0
    while ok and cnt < 12:
        print('    %-30s base=0x%08X size=0x%X'
              % (me.szModule, int(me.modBaseAddr or 0), int(me.modBaseSize)))
        ok = k32.Module32NextW(sh, ctypes.byref(me))
        cnt += 1
    k32.CloseHandle(sh)

print()
print('=== 2. 0x400000 处是否 MZ ===')
d = rpm(h, 0x00400000, 64)
print('  read=', 'OK' if d else 'FAIL', 'err=', ctypes.get_last_error())
if d:
    print('  head=', d[:32].hex())

print()
print('=== 3. 0x00DE07A4 可读性 ===')
d = rpm(h, 0x00DE07A4, 32)
print('  read=', 'OK' if d else 'FAIL', 'err=', ctypes.get_last_error())
if d:
    print('  data=', d.hex())
    print('  dwords=', ['0x%08X' % v for v in struct.unpack_from('<8I', d, 0)])

print()
print('=== 4. 0x00DE0000 附近区域状态 ===')
mbi = MBI()
ok = k32.VirtualQueryEx(h, ctypes.c_void_p(0x00DE0000), ctypes.byref(mbi), ctypes.sizeof(mbi))
if ok:
    print('  base=0x%08X size=0x%X state=0x%X protect=0x%X type=0x%X'
          % (int(mbi.BaseAddress), int(mbi.RegionSize), mbi.State, mbi.Protect, mbi.Type))
else:
    print('  VirtualQueryEx 失败 err=', ctypes.get_last_error())

print()
print('=== 5. 找主模块真实基址（扫 MZ 头, 只找第一个大区域） ===')
va = 0x10000
found = 0
while va < 0x7FFF0000 and found < 5:
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(va), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    size = int(mbi.RegionSize) or 0x1000
    base = int(mbi.BaseAddress)
    if mbi.State == 0x1000 and mbi.Type == 0x1000000:   # MEM_IMAGE
        d = rpm(h, base, 2)
        if d == b'MZ':
            d2 = rpm(h, base + 0x3C, 4)
            if d2:
                e_lfanew = struct.unpack('<I', d2)[0]
                if 0 < e_lfanew < 0x1000:
                    pe = rpm(h, base + e_lfanew, 4)
                    if pe == b'PE\x00\x00':
                        print('  MZ+PE @ 0x%08X  size=0x%X' % (base, size))
                        found += 1
    va = base + size
k32.CloseHandle(h)
