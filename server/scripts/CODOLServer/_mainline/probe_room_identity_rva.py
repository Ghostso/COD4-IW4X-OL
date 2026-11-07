"""定位 dwLobbyEventHandler 实例并定点轮询 +0x18/+0x1c（RVA 版）。

★ 关键修正（2026-10-28）:
    旧版直接扫绝对地址 0x00DE07A4，换进程后读不到。
    实测该 EXE 的 ImageBase=0x00400000 且 **未开 ASLR**
    (DllCharacteristics=0x8100, 无 DYNAMIC_BASE)，
    所以主模块基址应恒为 0x400000。但仍改为**运行时枚举模块取基址**，
    再按 RVA = 0x00DE07A4 - 0x400000 计算，避免任何假设。

流程:
    阶段0  枚举模块，算出本进程的 vtable 实际地址；读一次自检
    阶段A  扫 MEM_PRIVATE/MEM_IMAGE 找 vtable 指针（定位实例）
    阶段B  定点轮询实例 +0x18/+0x1c

用法:
    python -X utf8 -u probe_room_identity_rva.py <outdir> <roomId_hex> <secs> [interval_ms]
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

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
k32.Module32FirstW = k32.Module32FirstW
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(ME32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(ME32W)]

TARGET = "codoMP_client_shipRetail.exe"
VT_RVA = 0x00DE07A4 - 0x00400000     # 0x9E07A4
READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)


def find_pids():
    sh = k32.CreateToolhelp32Snapshot(2, 0)
    e = PE32W()
    e.dwSize = ctypes.sizeof(e)
    out = []
    ok = k32.Process32FirstW(sh, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(sh, ctypes.byref(e))
    k32.CloseHandle(sh)
    return out


def module_base(pid):
    sh = k32.CreateToolhelp32Snapshot(0x18, pid)
    if not sh or sh == ctypes.c_void_p(-1).value:
        return None
    me = ME32W()
    me.dwSize = ctypes.sizeof(me)
    base = None
    ok = k32.Module32FirstW(sh, ctypes.byref(me))
    while ok:
        if me.szModule.lower() == TARGET.lower():
            base = int(me.modBaseAddr or 0)
            break
        ok = k32.Module32NextW(sh, ctypes.byref(me))
    k32.CloseHandle(sh)
    return base


def rpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None


def iter_regions(h, want_private):
    va = 0x10000
    mbi = MBI()
    while va < 0x7FFF0000:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(va), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        size = int(mbi.RegionSize) or 0x1000
        base = int(mbi.BaseAddress)
        if (mbi.State == 0x1000 and not (mbi.Protect & 0x100)
                and (mbi.Protect & READABLE)):
            if want_private:
                if mbi.Type == 0x20000:
                    yield base, size
            else:
                yield base, size, mbi.Type
        va = base + size


def locate(h, vt):
    needle = struct.pack('<I', vt)
    hits = []
    for base, size in iter_regions(h, True):
        if size > (128 << 20):
            continue
        off = 0
        tail = b''
        while off < size:
            n = min(1 << 20, size - off)
            data = rpm(h, base + off, n)
            if data:
                blob = tail + data
                i = blob.find(needle)
                while i >= 0:
                    a = base + off - len(tail) + i
                    if a % 4 == 0:
                        hits.append(a)
                    i = blob.find(needle, i + 1)
                tail = data[-4:]
            off += n
    return hits


def main():
    outdir = sys.argv[1]
    room_id = int(sys.argv[2], 16)
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
    interval = (float(sys.argv[4]) if len(sys.argv) > 4 else 200.0) / 1000.0
    out = os.path.join(outdir, 'room_identity_rva.jsonl')

    pids = find_pids()
    if not pids:
        print('客户端未运行')
        return 1
    pid = pids[0]
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d' % ctypes.get_last_error())
        return 2

    base = module_base(pid)
    print('pid=%d handle=0x%X  EXE base=%s' % (pid, h, ('0x%08X' % base) if base else '?'))
    if base is None:
        base = 0x00400000
        print('  (枚举失败, 回退假定 0x400000)')
    vt = base + VT_RVA
    print('  vtable = base + 0x%X = 0x%08X' % (VT_RVA, vt))

    probe = rpm(h, vt, 0x20)
    if not probe:
        print('  ★ vtable 读取失败 —— 该地址不可读, 无法继续')
        return 3
    print('  自检: vtable 前 8 dword = %s'
          % ['0x%08X' % v for v in struct.unpack_from('<8I', probe, 0)])

    hi, lo = (room_id >> 32) & 0xFFFFFFFF, room_id & 0xFFFFFFFF
    print('  roomId hi=0x%08X lo=0x%08X' % (hi, lo))

    targets, last = [], -1e9
    t0 = time.time()
    with open(out, 'w', encoding='utf-8') as f:
        while time.time() - t0 < secs:
            now = time.time() - t0
            if not targets or now - last > 10.0:
                found = locate(h, vt)
                last = now
                if found != targets:
                    print('  [t=%.0fs] 实例 %s' % (now, [hex(x) for x in found]))
                targets = found
            rec = {'t': round(now, 2), 'n': len(targets), 'hit': []}
            for va in targets:
                d = rpm(h, va, 0x20)
                if not d or len(d) < 0x20:
                    continue
                w = struct.unpack_from('<8I', d, 0)
                item = {'va': '0x%08X' % va, 'p10': '0x%08X' % w[4],
                        'p14': '0x%08X' % w[5], 'p18': '0x%08X' % w[6],
                        'p1c': '0x%08X' % w[7],
                        'eq_hi': w[6] == hi, 'eq_lo': w[7] == lo}
                rec['hit'].append(item)
                if w[6] or w[7]:
                    print('  [t=%.1fs] ★ %s +18=%s +1c=%s  (roomId匹配=%s/%s)'
                          % (now, item['va'], item['p18'], item['p1c'],
                             item['eq_hi'], item['eq_lo']))
            f.write(json.dumps(rec) + '\n')
            f.flush()
            time.sleep(interval)

    k32.CloseHandle(h)
    print('done -> %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
