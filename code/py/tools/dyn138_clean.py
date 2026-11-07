#!/usr/bin/env python3
"""138 · 提权清理器（经 elevated agent 运行）：杀掉客户端 + 3074 监听 + UDP28960 占用者。
服务器是 agent(提权) 拉起的 => 非提权 taskkill 会被拒, 所以清理必须提权执行。

用法: python -I dyn138_clean.py --keep <agent_pid> [--quiet]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import re
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
TARGET = "codoMP_client_shipRetail.exe"


def pids_by_name():
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


def pids_on_port(port, udp=False):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         errors="replace").stdout
    pids = set()
    pat = re.compile(r"[:.]%d\s" % port)
    for ln in out.splitlines():
        if pat.search(ln) and (("UDP" in ln) == udp):
            toks = ln.split()
            if toks and toks[-1].isdigit():
                pids.add(int(toks[-1]))
    return sorted(pids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=-1)
    a = ap.parse_args()
    killed = []
    for pid in pids_by_name():
        if pid == a.keep:
            continue
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        killed.append(("client", pid))
    for pid in pids_on_port(3074) + pids_on_port(28960, udp=True):
        if pid in (a.keep, 0):
            continue
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        killed.append(("srv", pid))
    time.sleep(1)
    print("clean: killed=%s ; 剩 3074=%s 28960=%s client=%s"
          % (killed, pids_on_port(3074), pids_on_port(28960, udp=True), pids_by_name()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
