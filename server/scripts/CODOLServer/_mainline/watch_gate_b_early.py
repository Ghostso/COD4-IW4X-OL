"""抢早期句柄，然后高频采样自动开局链的闸门B（obj+0x10614）。

为什么必须这样：
  客户端被 ACE/TP3 保护之后，**后开的**进程句柄 OpenProcess 能成功但
  ReadProcessMemory 一律 err=5。只有在进程刚出现时抢到的**早期句柄**
  才一直可读（本项目 1585MB 全内存转储就是这么拿到的）。
  cdb 附加也不行：ACE-GAME 驱动直接返回 STATUS_ACCESS_DENIED(0xC0000022)。

采样的量：
  [0x082E13FC]                全局单例
  单例+0x10614                 ★闸门B（自动开局状态机的前置条件）
  单例+0x283 / +0x38710        闸门A 的两个条件
  [0x0849B61C]                已请求开局标志
  dw_autoStartGame / dw_enterRoomCountingDown 的当前值

只读。用法:
  python -X utf8 watch_gate_b_early.py <out.txt> [秒数] [采样间隔秒]
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

TARGET = "codoMP_client_shipRetail.exe"
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.argtypes = [wt.HANDLE]
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(ctypes.c_int64)]
advapi32.AdjustTokenPrivileges.argtypes = [wt.HANDLE, wt.BOOL, ctypes.c_void_p,
                                           wt.DWORD, ctypes.c_void_p, ctypes.c_void_p]

G_SINGLETON = 0x082E13FC
G_STARTED = 0x0849B61C
G_AUTOSTART = 0x0849B7A4
G_ROOMCD = 0x0849B7C4


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


def enable_debug():
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
    if not h or h == wt.HANDLE(-1).value:
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


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "gateb_early.txt"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.005
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    log = open(out, "w", encoding="utf-8")
    t0 = time.time()

    def w(msg):
        line = "[%8.3fs] %s" % (time.time() - t0, msg)
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    dbg, derr = enable_debug()
    w("SeDebugPrivilege = %s (err=%d)" % (dbg, derr))

    pid = None
    h = None
    while time.time() - t0 < 600:
        p = find_pid(TARGET)
        if p is not None:
            pid = p
            h = k32.OpenProcess(PROC_ALL, False, pid)
            if h:
                w("★ 抢到早期句柄 pid=%d handle=0x%X (t+%.2fs)" % (pid, h, time.time() - t0))
                break
            w("OpenProcess 失败 pid=%d err=%d，重试" % (pid, ctypes.get_last_error()))
        time.sleep(0.01)
    if not h:
        w("未能取得句柄")
        return 2

    b = rd(h, 0x00400000, 4)
    w("早读 0x00400000 = %s (err=%d)" % (b.hex() if b else "失败", ctypes.get_last_error()))

    prev = None
    prev_gate = None
    n_read_fail = 0
    while time.time() - t0 < secs:
        sing = rd(h, G_SINGLETON, 4)
        if sing is None:
            n_read_fail += 1
            if n_read_fail == 1:
                w("读 [0x%08X] 失败 err=%d" % (G_SINGLETON, ctypes.get_last_error()))
            time.sleep(step)
            continue
        s = struct.unpack("<I", sing)[0]
        if s == 0:
            time.sleep(step)
            continue
        # 单例出来了
        gate = rd(h, s + 0x10614, 1)
        st = rd(h, G_STARTED, 1)
        au = rd(h, G_AUTOSTART, 4)
        rc = rd(h, G_ROOMCD, 4)
        b283 = rd(h, s + 0x283, 1)
        b387 = rd(h, s + 0x38710, 1)
        st20 = rd(h, s + 0x20, 4)
        gv = gate[0] if gate else None
        cur = (s, gv, st[0] if st else None,
               struct.unpack("<I", au)[0] if au else None,
               struct.unpack("<I", rc)[0] if rc else None,
               b283[0] if b283 else None, b387[0] if b387 else None,
               struct.unpack("<I", st20)[0] if st20 else None)
        if cur != prev:
            w("single=0x%08X gateB=%s started=%s state20=0x%08X b283=%s b38710=%s autoHandle=0x%08X roomcdHandle=0x%08X"
              % (cur[0], cur[1], cur[2], cur[7] or 0, cur[5], cur[6],
                 cur[3] or 0, cur[4] or 0))
            prev = cur
        if gv is not None and prev_gate == 0 and gv != 0:
            w("★★★ 闸门B 从 0 变 %d  t=%.3fs" % (gv, time.time() - t0))
        prev_gate = gv
        # 顺带读 dvar 值
        if au:
            ah = struct.unpack("<I", au)[0]
            v = rd(h, ah + 0xC, 4) if ah else None
            if v:
                w("    dw_autoStartGame = %d" % struct.unpack("<I", v)[0])
        time.sleep(step)
    w("结束 (读失败 %d 次)" % n_read_fail)
    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
