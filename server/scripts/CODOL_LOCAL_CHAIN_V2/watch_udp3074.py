# -*- coding: utf-8 -*-
"""抓 UDP 3074 的所有流量（含外发），确认客户端是否在发 DW NAT 探测。"""
import ctypes
import ctypes.wintypes as wt
import socket
import struct
import subprocess
import sys
import threading
import time

# 同时做两件事：
#  1) 嗅探：绑 0.0.0.0:3074 收本地包（会挡住本机 STUN，所以只在 --bind 时启用）
#  2) 通过 netstat 轮询查看客户端有没有 UDP 3074 端点
#
# 更实用的做法：直接看客户端的 UDP 端点表（netstat），
# 以及用 tshark 过滤 udp port 3074。


def pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         errors="replace").stdout
    r = []
    for line in out.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if len(c) >= 2 and c[0].lower() == "codomp_client_shipretail.exe":
            try:
                r.append(int(c[1]))
            except ValueError:
                pass
    return r


def udp_endpoints(pid):
    out = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                         capture_output=True, text=True, errors="replace").stdout
    rows = []
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 4 and p[-1] == str(pid):
            rows.append(p[1])
    return rows


def netstat_3074(pid):
    """看是否有 3074 相关的 UDP 端点（任意远端）。"""
    out = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                         capture_output=True, text=True, errors="replace").stdout
    hits = []
    for ln in out.splitlines():
        if "3074" in ln:
            hits.append(ln.strip())
    return hits


def main():
    t0 = time.time()
    seen = set()
    print("watching UDP endpoints...", flush=True)
    while time.time() - t0 < 100:
        for cp in pids():
            if cp in seen:
                continue
            seen.add(cp)
            print("\n=== pid=%d ===" % cp, flush=True)
            for k in range(26):
                time.sleep(1)
                if cp not in pids():
                    print("  t+%ds 退出" % (k + 1), flush=True)
                    break
                eps = udp_endpoints(cp)
                interesting = [e for e in eps if e.endswith(":3074")]
                s = "  t+%2ds UDP端点=%d" % (k + 1, len(eps))
                if interesting:
                    s += "  ★3074: %s" % ",".join(interesting)
                if eps and k % 3 == 0:
                    s += "  [%s]" % " ".join(e.split(":")[-1] for e in eps[:8])
                print(s, flush=True)
        time.sleep(0.3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
