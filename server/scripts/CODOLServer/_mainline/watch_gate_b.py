"""在活客户端里持续采样自动开局链的状态。

链路（静态逆向）：
  0x63C5E9  mov ecx,[0x82E13FC]      -> 全局单例
  0x63C5F1  call [eax+0x60]          -> 闸门A  0x0062FE30
  0x63C606  call [eax+0x64]          -> 闸门B  0x0062FE80
  0x62FE80  cmp byte [ecx+0x10614],0 -> 闸门B 读的字节
  0x63C970  状态5 = 自动开局，置 [0x849B61C]=1

同时采样：
  [0x849B61C]  已请求开局标志
  [0x849B7A4]  dw_autoStartGame 句柄 -> +0xC 值
  [0x849B7C4]  dw_enterRoomCountingDown 句柄 -> +0xC 值
  单例对象 +0x20 / +0x283 / +0x10614 / +0x38710

只读，不写目标进程。
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
TARGET = "codoMP_client_shipRetail.exe"
TH32CS_SNAPPROCESS = 0x00000002
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

G_SINGLETON = 0x082E13FC
G_STARTED = 0x0849B61C
G_AUTOSTART = 0x0849B7A4
G_ROOMCD = 0x0849B7C4


def rpm(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
    if not ok or got.value != n:
        return None
    return buf.raw


def u32(h, addr):
    b = rpm(h, addr, 4)
    return struct.unpack("<I", b)[0] if b else None


def find_pid(name):
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == -1:
        return None

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    ok = k32.Process32First(h, ctypes.byref(pe))
    found = None
    while ok:
        if pe.szExeFile.decode(errors="replace").casefold() == name.casefold():
            found = pe.th32ProcessID
            break
        ok = k32.Process32Next(h, ctypes.byref(pe))
    k32.CloseHandle(h)
    return found


def snapshot(h):
    d = {}
    d["single"] = u32(h, G_SINGLETON)
    d["started"] = rpm(h, G_STARTED, 1)
    d["started"] = d["started"][0] if d["started"] else None
    ah = u32(h, G_AUTOSTART)
    rh = u32(h, G_ROOMCD)
    d["autostart"] = u32(h, ah + 0xC) if ah else None
    d["roomcd"] = u32(h, rh + 0xC) if rh else None
    s = d["single"]
    if s:
        bb = rpm(h, s + 0x283, 1)
        d["b283"] = bb[0] if bb else None
        bb = rpm(h, s + 0x38710, 1)
        d["b38710"] = bb[0] if bb else None
        bb = rpm(h, s + 0x10614, 1)
        d["gateB"] = bb[0] if bb else None
        st = u32(h, s + 0x20)
        d["state20"] = st
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--out", default="gateb_watch.txt")
    a = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    log = open(a.out, "w", encoding="utf-8")
    t0 = time.time()

    def w(msg):
        line = "[%7.2fs] %s" % (time.time() - t0, msg)
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    pid = None
    while time.time() - t0 < 30:
        pid = find_pid(TARGET)
        if pid:
            break
        time.sleep(0.05)
    if not pid:
        w("客户端没起来")
        return 1
    w("pid=%d" % pid)
    h = k32.OpenProcess(PROC_ALL, False, pid)
    if not h:
        w("OpenProcess err=%d" % ctypes.get_last_error())
        return 1
    w("句柄 OK")

    prev = None
    while time.time() - t0 < a.seconds:
        d = snapshot(h)
        if d != prev:
            parts = []
            for k in ("single", "started", "autostart", "roomcd",
                      "state20", "b283", "b38710", "gateB"):
                if k in d:
                    v = d[k]
                    parts.append("%s=%s" % (k, ("0x%08X" % v) if isinstance(v, int) and v and v > 0xFF else v))
            w(" ".join(parts))
            prev = d
            if d.get("gateB") not in (None, 0):
                w("★★★ 闸门B 变为非零! 触发时刻 t=%.2fs" % (time.time() - t0))
        time.sleep(a.step)
    w("结束")
    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
