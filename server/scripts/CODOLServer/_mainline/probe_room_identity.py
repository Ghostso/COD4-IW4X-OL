"""定位 dwLobbyEventHandler 实例并**定点**轮询其 +0x18/+0x1c。

两阶段:
  阶段A: 扫一次全用户空间找 vtable 0x00DE07A4（只在启动时做一次，慢）
  阶段B: 只读已定位实例的 +0x18/+0x1c（微秒级），高频轮询
  若阶段B 读失败(实例被释放/迁移)，回到阶段A 重定位。

用法:
    python -X utf8 -u probe_room_identity.py <outdir> <roomId_hex> <secs> [interval_ms]
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL

TARGET = "codoMP_client_shipRetail.exe"
VTABLE = 0x00DE07A4
READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)


def find_pids():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = []
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


def rpm(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None


def iter_regions(h, private_only=True):
    va = 0x10000
    mbi = MEMORY_BASIC_INFORMATION()
    while va < 0x7FFF0000:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(va), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        size = int(mbi.RegionSize) or 0x1000
        base = int(mbi.BaseAddress)
        if (mbi.State == 0x1000 and not (mbi.Protect & 0x100)
                and (mbi.Protect & READABLE)):
            if (not private_only) or mbi.Type == 0x20000:   # MEM_PRIVATE
                yield base, size
        va = base + size


def locate(h):
    """扫 MEM_PRIVATE 区域找 vtable，返回候选实例地址列表。"""
    needle = struct.pack('<I', VTABLE)
    hits = []
    for base, size in iter_regions(h, private_only=True):
        if size > 64 << 20:          # 跳超大区，避免卡死
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
                    va = base + off - len(tail) + i
                    if va % 4 == 0:
                        # 只收"看起来像实例"的：+0x0C 是小整数
                        d = rpm(h, va + 0x0C, 4)
                        if d and struct.unpack('<I', d)[0] < 0x1000:
                            hits.append(va)
                    i = blob.find(needle, i + 1)
                tail = data[-4:] if len(data) >= 4 else data
            off += n
    return hits


def main():
    outdir = sys.argv[1]
    room_id = int(sys.argv[2], 16)
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0
    interval = (float(sys.argv[4]) if len(sys.argv) > 4 else 200.0) / 1000.0
    out = os.path.join(outdir, 'room_identity.jsonl')

    pids = find_pids()
    if not pids:
        print('客户端未运行')
        return 1
    h = k32.OpenProcess(0x0410, False, pids[0])
    if not h:
        print('OpenProcess 失败 err=%d' % ctypes.get_last_error())
        return 2

    hi = (room_id >> 32) & 0xFFFFFFFF
    lo = room_id & 0xFFFFFFFF
    print('pid=%d roomId=0x%016X (hi=0x%08X lo=0x%08X)' % (pids[0], room_id, hi, lo))

    targets = []
    t0 = time.time()
    last_locate = 0.0
    with open(out, 'w', encoding='utf-8') as f:
        while time.time() - t0 < secs:
            now = time.time() - t0
            if not targets or now - last_locate > 10.0:
                found = locate(h)
                last_locate = now
                if found != targets:
                    print('  [t=%.0fs] 定位实例 %s' % (now, [hex(x) for x in found]))
                targets = found
            rec = {'t': round(now, 2), 'instances': []}
            for va in targets:
                d = rpm(h, va, 0x20)
                if not d or len(d) < 0x20:
                    continue
                w = struct.unpack_from('<8I', d, 0)
                rec['instances'].append({
                    'va': '0x%08X' % va,
                    'vt': '0x%08X' % w[0],
                    'w4': '0x%08X' % w[1], 'w8': '0x%08X' % w[2],
                    'wC': '0x%08X' % w[3],
                    'p10': '0x%08X' % w[4], 'p14': '0x%08X' % w[5],
                    'p18': '0x%08X' % w[6], 'p1c': '0x%08X' % w[7],
                    'is_roomid_hi': w[6] == hi, 'is_roomid_lo': w[7] == lo,
                    'nonzero': bool(w[6] or w[7]),
                })
            f.write(json.dumps(rec) + '\n')
            f.flush()
            nz = [i for i in rec['instances'] if i['nonzero']]
            if nz:
                print('  [t=%.1fs] ★ 非零身份: %s'
                      % (now, [(i['va'], i['p18'], i['p1c']) for i in nz]))
            time.sleep(interval)

    k32.CloseHandle(h)
    print('done -> %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
