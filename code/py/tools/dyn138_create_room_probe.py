#!/usr/bin/env python3
"""138: 「点创建房间 -> 大厅秒断秒恢复」专项观测（只读）。

不解密、不改链，只做三件事：
  1. 每 100ms 记录 3074/3074-远端 的连接状态（谁先 FIN/RST）
  2. 每 2s 采样房间对象链路（0x82E13FC / 成员表 / 0x76446B0 / 0x849B61C）
  3. 客户端进程存活与 PID 变化（判断是"重连"还是"进程重启"）
用法: python -I dyn138_create_room_probe.py <outfile> [--secs 400]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
TARGET = "codoMP_client_shipRetail.exe"


def pids():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = []
    e = PE32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


def rd(h, va, n):
    if not h:
        return b""
    b = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
        return b.raw[:got.value]
    return b""


def u32(h, va):
    d = rd(h, va, 4)
    return struct.unpack("<I", d)[0] if len(d) == 4 else None


def tcp_state():
    """返回 3074 相关连接快照 + 客户端 TCP 连接数（用 netstat，不依赖 PS）。"""
    try:
        o = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                           errors="replace", timeout=5).stdout
    except Exception:
        return None
    rows = []
    for ln in o.splitlines():
        if ":3074" in ln and ("TCP" in ln or "UDP" in ln):
            rows.append(" ".join(ln.split()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outfile")
    ap.add_argument("--secs", type=float, default=400)
    a = ap.parse_args()
    f = open(a.outfile, "w", encoding="utf-8")

    def say(s):
        line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
        print(line, flush=True)
        f.write(line + "\n")
        f.flush()

    say("=== 观测开始（只读）。请在进大厅后点【创建房间】 ===")

    # 抢早期句柄
    t0 = time.time()
    pid = None
    while time.time() - t0 < 240:
        ps = pids()
        if ps:
            pid = ps[0]
            break
        time.sleep(0.05)
    if not pid:
        say("!! 未见客户端")
        return 2
    h = k32.OpenProcess(0x400 | 0x10, False, pid)
    say("客户端 pid=%d (t+%.2fs) h=%s 自证=%s"
        % (pid, time.time() - t0, h,
           rd(h, 0x400000, 4).hex()))

    prev_tcp = None
    prev_pid = pid
    last_sample = 0.0
    while time.time() - t0 < a.secs:
        rel = time.time() - t0
        # --- 100ms: TCP 状态变化 ---
        cur = tcp_state()
        if cur is not None and cur != prev_tcp:
            if prev_tcp is not None:
                added = [x for x in cur if x not in prev_tcp]
                gone = [x for x in prev_tcp if x not in cur]
                if added or gone:
                    say("★ TCP 变化 t+%.1f" % rel)
                    for x in gone:
                        say("     - %s" % x)
                    for x in added:
                        say("     + %s" % x)
            prev_tcp = cur
        # --- 进程存活/PID 变化 ---
        ps = pids()
        if not ps:
            say("★ 客户端进程消失 t+%.1f" % rel)
            break
        if ps[0] != prev_pid:
            say("★ 客户端 PID 变化 %d -> %d t+%.1f（=进程重启，非重连）"
                % (prev_pid, ps[0], rel))
            prev_pid = ps[0]
            h = k32.OpenProcess(0x400 | 0x10, False, prev_pid)
        # --- 2s: 房间对象 ---
        if rel - last_sample >= 2.0:
            last_sample = rel
            parts = []
            for nm, va in (("gate0x849BA30", 0x0849BA30), ("state0x849BA34", 0x0849BA34),
                           ("gate2_0x76446B0", 0x076446B0),
                           ("started0x849B61C", 0x0849B61C),
                           ("roomSlot", 0x082E13FC), ("connSlot", 0x08269774)):
                v = u32(h, va)
                parts.append("%s=%s" % (nm, ("%08X" % v) if v is not None else "?"))
            room = u32(h, 0x082E13FC)
            if room and room > 0x10000:
                n = u32(h, room + 0x105D8)
                cap = u32(h, room + 0x105FE)
                built = u32(h, room + 0x278)
                parts.append("n=%s cap=%s built=%s" % (n, cap, built))
                if n is not None and 0 < n <= 19:
                    for i in range(min(n, 19)):
                        ra = room + 0xE368 + i * 0x1D0
                        uid = rd(h, ra, 8)
                        tm = u32(h, ra + 0x88)
                        rdy = u32(h, ra + 0x90)
                        parts.append("<%d:%s t=%s r=%s>"
                                     % (i, uid.hex() if len(uid) == 8 else "?",
                                        hex(tm) if tm is not None else "?",
                                        hex(rdy) if rdy is not None else "?"))
            say("t+%.1f %s" % (rel, " ".join(parts)))
        time.sleep(0.1)
    say("=== 观测结束 ===")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
