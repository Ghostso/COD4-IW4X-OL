"""确认 0x00DE07A4 所在的模块与相对偏移, 以便在新进程里重算地址。

思路: 该 VA 在旧转储里属于某个模块。列出进程里所有模块的基址/大小,
找出包含 0x00DE07A4 的模块 -> 得到 RVA, 再给出本轮实际地址。
如果 EXE 是固定基址(无 ASLR), 地址应不变; 若变化, 就在这里显示新值。
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class PE32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", wt.WCHAR * 256), ("szExePath", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
MODULE = 0x00000008 | 0x00000002  # TH32CS_SNAPMODULE


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
    print('客户端未运行')
    raise SystemExit(1)
pid = p[0]
print('pid=%d' % pid)

sh = k32.CreateToolhelp32Snapshot(0x8 | 0x10, pid)
if not sh or sh == -1:
    print('snapshot modules failed err=%d' % ctypes.get_last_error())
    raise SystemExit(2)

me = MODULEENTRY32W()
me.dwSize = ctypes.sizeof(me)
mods = []
ok = k32.Module32FirstW(sh, ctypes.byref(me))
while ok:
    base = int(me.modBaseAddr or 0)
    size = int(me.modBaseSize)
    mods.append((base, size, me.szModule, me.szExePath))
    ok = k32.Module32NextW(sh, ctypes.byref(me))
k32.CloseHandle(sh)

print('模块数=%d' % len(mods))
print()
OLD = 0x00DE07A4
print('=== 包含旧地址 0x%08X 的模块 ===' % OLD)
found = None
for base, size, name, path in mods:
    if base <= OLD < base + size:
        found = (base, size, name, path)
        print('  %s  基址=0x%08X 大小=0x%X  RVA=0x%X'
              % (name, base, size, OLD - base))
if not found:
    print('  未找到（旧地址不在任何当前模块范围内）')

print()
print('=== 主 EXE 与会话相关的关键模块 ===')
for base, size, name, path in mods:
    ln = name.lower()
    if ln.endswith('shipretail.exe') or 'ace' in ln or 'policyprobe' in ln:
        print('  %-28s 0x%08X  0x%X' % (name, base, size))

print()
print('=== 若 EXE 基址有变化，vtable 的新地址 ===')
for base, size, name, path in mods:
    if name.lower().endswith('shipretail.exe'):
        rva = OLD - base if base <= OLD < base + size else None
        if rva is None:
            # 用旧转储时的假定基址 0x400000 反推 RVA
            rva = OLD - 0x400000
        print('  EXE 基址 = 0x%08X' % base)
        print('  假定 RVA = 0x%X' % rva)
        print('  本轮 vtable 地址 = 0x%08X' % (base + rva))
