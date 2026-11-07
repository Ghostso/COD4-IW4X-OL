"""抢最早句柄 + 立即开始增量转储，用来抓 obj+0x10614 的初始化过程。

背景：ACE 会在进程启动后收紧策略，之后 ReadProcessMemory 一律 err=5。
所以句柄一到手就必须**立刻**读，并且反复重读，把不同时刻的变化都记下来。

输出（都写到 outdir）：
  snap_<k>_<t>.bin   第 k 轮的全地址空间快照（稀疏：只写读成功的部分）
  log.txt            时序 + 每轮读成功的字节数 + 目标字段的变化

目标字段通过**每次快照重新解析**得到，因为地址在 ASLR 下会变：
  [0x082E13FC] -> 单例对象，闸门B 在 单例+0x10614

只读。
用法:
  python -X utf8 dump_earliest.py <outdir> <秒数> <轮次间隔秒>
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

TARGET = "codoMP_client_shipRetail.exe"
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

G_SINGLETON = 0x082E13FC
GATE_B_OFF = 0x10614

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_size_t]
k32.CloseHandle.argtypes = [wt.HANDLE]


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


def enable_debug():
    advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                          ctypes.POINTER(wt.HANDLE)]
    advapi32.OpenProcessToken.restype = wt.BOOL
    advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                               ctypes.POINTER(ctypes.c_int64)]
    advapi32.AdjustTokenPrivileges.argtypes = [wt.HANDLE, wt.BOOL, ctypes.c_void_p,
                                               wt.DWORD, ctypes.c_void_p,
                                               ctypes.c_void_p]
    htok = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(), 0x0020 | 0x0008,
                                     ctypes.byref(htok)):
        return False, ctypes.get_last_error()
    luid = ctypes.c_int64()
    if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege",
                                          ctypes.byref(luid)):
        return False, ctypes.get_last_error()

    class LAA(ctypes.Structure):
        _fields_ = [("Luid", ctypes.c_int64), ("Attr", wt.DWORD)]

    class TP(ctypes.Structure):
        _fields_ = [("n", wt.DWORD), ("p", LAA * 1)]

    tp = TP(1, (LAA * 1)(LAA(luid.value, 0x00000002)))
    ok = advapi32.AdjustTokenPrivileges(htok, False, ctypes.byref(tp), 0, None, None)
    return bool(ok), ctypes.get_last_error()


def find_pid(name):
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    h = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not h:
        return None
    pe = PE32()
    pe.dwSize = ctypes.sizeof(PE32)
    ok = k32.Process32First(h, ctypes.byref(pe))
    found = None
    while ok:
        if pe.szExeFile.decode(errors="replace").casefold() == name.casefold():
            found = pe.th32ProcessID
            break
        ok = k32.Process32Next(h, ctypes.byref(pe))
    k32.CloseHandle(h)
    return found


def rd(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n,
                                 ctypes.byref(got)) or got.value != n:
        return None
    return buf.raw


def regions(h, lo, hi):
    out = []
    addr = lo
    mbi = MBI()
    while addr < hi:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                  ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        b = mbi.BaseAddress or 0
        s = mbi.RegionSize or 0
        if s == 0:
            break
        b0, s0 = b, s
        if b0 < lo:
            s0 -= (lo - b0)
            b0 = lo
        if b0 + s0 > hi:
            s0 = hi - b0
        if s0 > 0:
            out.append((b0, s0, int(mbi.State), int(mbi.Protect)))
        nxt = b + s
        if nxt <= addr:
            break
        addr = nxt
    return out


def w(log, t0, msg):
    line = "[%8.3fs] %s" % (time.time() - t0, msg)
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def main():
    outdir = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    os.makedirs(outdir, exist_ok=True)
    log = open(os.path.join(outdir, "log.txt"), "w", encoding="utf-8")
    t0 = time.time()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    dbg, derr = enable_debug()
    w(log, t0, "SeDebugPrivilege=%s err=%d" % (dbg, derr))

    pid = None
    h = None
    while time.time() - t0 < 600:
        p = find_pid(TARGET)
        if p is not None:
            pid = p
            h = k32.OpenProcess(PROC_ALL, False, pid)
            if h:
                w(log, t0, "★ 句柄到手 pid=%d handle=0x%X" % (pid, h))
                break
            w(log, t0, "OpenProcess 失败 err=%d" % ctypes.get_last_error())
        time.sleep(0.005)
    if not h:
        w(log, t0, "拿不到句柄")
        return 2

    # 立刻首读，判断还有没有窗口
    first = rd(h, 0x00400000, 4)
    w(log, t0, "首读 0x00400000 = %s" % (first.hex() if first else "失败 err=%d" % ctypes.get_last_error()))

    lo, hi = 0x00010000, 0x7FFF0000
    idx = 0
    while time.time() - t0 < secs:
        R = regions(h, lo, hi)
        img = bytearray(hi - lo)
        covered = bytearray(hi - lo)
        total = 0
        fails = 0
        for b, s, state, prot in R:
            if state != MEM_COMMIT:
                continue
            if prot & PAGE_GUARD:
                continue
            if (prot & 0xFF) == PAGE_NOACCESS:
                continue
            p = 0
            while p < s:
                n = min(0x40000, s - p)
                buf = ctypes.create_string_buffer(n)
                g = ctypes.c_size_t(0)
                if (k32.ReadProcessMemory(h, ctypes.c_void_p(b + p), buf, n,
                                          ctypes.byref(g)) and g.value):
                    off = b - lo + p
                    img[off:off + g.value] = buf.raw[:g.value]
                    covered[off:off + g.value] = b"\x01" * g.value
                    total += g.value
                    p += n
                else:
                    n2 = min(0x1000, s - p)
                    buf2 = ctypes.create_string_buffer(n2)
                    g2 = ctypes.c_size_t(0)
                    if (k32.ReadProcessMemory(h, ctypes.c_void_p(b + p), buf2,
                                              n2, ctypes.byref(g2)) and g2.value):
                        off = b - lo + p
                        img[off:off + g2.value] = buf2.raw[:g2.value]
                        covered[off:off + g2.value] = b"\x01" * g2.value
                        total += g2.value
                    else:
                        fails += 1
                    p += n2
        idx += 1
        tag = "snap_%03d" % idx
        with open(os.path.join(outdir, tag + ".bin"), "wb") as f:
            f.write(bytes(img))
        with open(os.path.join(outdir, tag + "_cover.bin"), "wb") as f:
            f.write(bytes(covered))
        with open(os.path.join(outdir, tag + ".json"), "w", encoding="utf-8") as f:
            json.dump({"index": idx, "t": time.time() - t0, "pid": pid,
                       "read_bytes": total, "fail_chunks": fails,
                       "regions": len(R), "lo": lo, "hi": hi,
                       "covered": sum(covered)}, f)
        # 目标字段
        sing = rd(h, G_SINGLETON, 4)
        sv = struct.unpack("<I", sing)[0] if sing else None
        gv = None
        if sv:
            gb = rd(h, sv + GATE_B_OFF, 1)
            gv = gb[0] if gb else None
        w(log, t0, "快照#%d 读到 %.1f MB (失败块 %d, 区域 %d) 单例=%s 闸门B=%s"
          % (idx, total / 1048576.0, fails, len(R),
             ("0x%08X" % sv) if sv else sv, gv))
        if time.time() - t0 >= secs:
            break
        time.sleep(gap)
    w(log, t0, "结束，共 %d 轮" % idx)
    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
