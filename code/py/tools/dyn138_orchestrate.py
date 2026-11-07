#!/usr/bin/env python3
"""138 动态卷编排: 原封链(不改) + 外部只读内存转储(经 elevated agent)。

- 链: run_frozen_chain_capture_once.py（**原封**，只传参数，不碰任何文件）
- 观测: mem_dump_attach.py（**只读**附加；文档明确"游戏由启动器拉起"）经 agent 提权运行
- 时序: 客户端出现后 ~25s 触发一次转储（记忆: t+23.8s 成功 / t+32.2s 失败）
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import socket
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
TARGET = "codoMP_client_shipRetail.exe"
AGENT_CFG = os.path.join(ROOT, "CODOLServer", "logs", "elevated_agent.json")
DUMP_DIR = os.path.join(ROOT, "run_codol_001", "runs", "R4_dump")
SECONDS = 200
DUMP_AT = 25           # 客户端出现后多少秒转储
MAX_MB = 400

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE


def client_pids():
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


def agent_run(argv, timeout=900):
    a = json.load(open(AGENT_CFG, encoding="utf-8"))
    req = json.dumps({"token": str(a["token"]), "action": "run", "argv": argv,
                      "cwd": ROOT, "timeout": timeout}).encode("utf-8") + b"\n"
    buf = b""
    with socket.create_connection(("127.0.0.1", int(a["port"])), timeout=timeout) as s:
        s.sendall(req)
        while not buf.endswith(b"\n"):
            c = s.recv(65536)
            if not c:
                break
            buf += c
    try:
        return json.loads(buf.decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": "bad agent json: %r" % (e,), "raw": buf[:200]}


def main():
    launcher = os.path.join(ROOT, "run_codol_001", "run_frozen_chain_capture_once.py")
    cmd = [sys.executable, "-X", "utf8", launcher,
           "--kit", "GOLDEN-LOBBY-001\\REF_LOBBY_KIT",
           "--data-kit", "CODOL_VERIFIED_GOLDEN_20261019",
           "--game-root", "COD OL", "--seconds", str(SECONDS)]
    print("[orch] 起原封链: %s" % " ".join(cmd[2:]), flush=True)
    lf = open(os.path.join(ROOT, "run_codol_001", "runs", "R4_chain_stdout.txt"),
              "w", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT)

    # 等客户端出现
    t0 = time.time()
    pid = None
    while time.time() - t0 < 120:
        ps = client_pids()
        if ps:
            pid = ps[0]
            break
        if p.poll() is not None:
            print("[orch] !! 启动器提前退出 rc=%s" % p.returncode, flush=True)
            break
        time.sleep(1)
    print("[orch] 客户端 pid=%s (t+%.1fs)" % (pid, time.time() - t0), flush=True)

    dump_rc = None
    if pid:
        # 等到 DUMP_AT 秒再转储（抢早期句柄窗口）
        while time.time() - t0 < DUMP_AT:
            time.sleep(0.5)
        os.makedirs(DUMP_DIR, exist_ok=True)
        print("[orch] t+%.1fs 经 agent 触发只读转储 -> %s" % (time.time() - t0, DUMP_DIR),
              flush=True)
        r = agent_run([sys.executable, "-I",
                       os.path.join(ROOT, "run_codol_001", "mem_dump_attach.py"),
                       DUMP_DIR, "--max-mb", str(MAX_MB)], timeout=600)
        dump_rc = r.get("rc")
        print("[orch] 转储 ok=%s rc=%s" % (r.get("ok"), dump_rc), flush=True)
        for k in ("stdout", "stderr"):
            if r.get(k):
                print("[dump:%s] %s" % (k, r[k].strip()), flush=True)

    rc = p.wait()
    lf.close()
    print("[orch] 链结束 rc=%s ; 转储 rc=%s" % (rc, dump_rc), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
