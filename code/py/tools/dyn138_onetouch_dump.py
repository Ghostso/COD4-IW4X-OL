#!/usr/bin/env python3
"""138 动态卷 · 一键转存（固化脚本）。

一条命令做完全部:
  1) 清掉上一轮的残留（客户端 / 3074 监听 / UDP 28960 占用者；**不碰 elevated agent**）
  2) 重置单发令牌（调用原封启动器的 --authorize-next-launch）
  3) 起**原封**链: run_frozen_chain_capture_once.py（只传参，不改任何文件）
  4) **立刻**经 elevated agent 运行 dyn138_watcher.py：
       客户端一出现(50ms 轮询)就 OpenProcess 抢**早期句柄** ->
       周期采样 20 个关键全局 -> 到点用**同一个早期句柄**做分块全量转储
  5) 等链结束, 打印 rc + 产物路径

用法(默认即可):
  python -X utf8 tools\dyn138_onetouch_dump.py
  python -X utf8 tools\dyn138_onetouch_dump.py --seconds 240 --full-at 45 --full-mb 400
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import datetime
import json
import os
import socket
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
RUNS = os.path.join(ROOT, "run_codol_001", "runs")
LAUNCHER = os.path.join(ROOT, "run_codol_001", "run_frozen_chain_capture_once.py")
WATCHER = os.path.join(ROOT, "tools", "dyn138_watcher.py")
AGENT_CFG = os.path.join(ROOT, "CODOLServer", "logs", "elevated_agent.json")
TARGET = "codoMP_client_shipRetail.exe"
KIT = "GOLDEN-LOBBY-001\\REF_LOBBY_KIT"
DATA_KIT = "CODOL_VERIFIED_GOLDEN_20261019"
GAME = "COD OL"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


def log(s):
    print("[1click] " + s, flush=True)


def agent():
    return json.load(open(AGENT_CFG, encoding="utf-8"))


def agent_run(argv, timeout=900):
    a = agent()
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
        return {"ok": False, "error": "bad json %r" % (e,), "raw": buf[:200]}


def kill_leftovers():
    """★ 清理必须**经 agent 提权**执行：链里的服务器是 agent(提权)拉起的，
    非提权 taskkill 会被拒（第 5 轮实测）=> 3074 不释放 => 原封启动器 rc=2 拒绝启动。"""
    a = agent()
    r = agent_run([sys.executable, "-I", os.path.join(ROOT, "tools", "dyn138_clean.py"),
                   "--keep", str(a["pid"])], timeout=180)
    log("提权清理: ok=%s rc=%s %s" % (r.get("ok"), r.get("rc"),
                                    (r.get("stdout") or r.get("error") or "").strip()))
    # 本地确认 3074 已释放（最多等 15s）
    for _ in range(15):
        try:
            with socket.create_connection(("127.0.0.1", 3074), timeout=.3):
                time.sleep(1)
                continue
        except OSError:
            return True
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=200)
    ap.add_argument("--full-at", type=float, default=45.0)
    ap.add_argument("--full-mb", type=int, default=400)
    ap.add_argument("--sample-secs", type=float, default=120.0)
    ap.add_argument("--outdir", default="")
    a = ap.parse_args()

    ag = agent()
    log("agent pid=%s port=%s debug_privilege=%s" % (ag.get("pid"), ag.get("port"),
                                                     ag.get("debug_privilege")))
    kill_leftovers()
    time.sleep(2)

    r = subprocess.run([sys.executable, "-X", "utf8", LAUNCHER,
                        "--authorize-next-launch", "--kit", KIT],
                       cwd=ROOT, capture_output=True, text=True, errors="replace")
    log("令牌重置: %s" % (r.stdout.strip() or r.stderr.strip()))

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = a.outdir or os.path.join(RUNS, "DUMP_" + stamp)
    os.makedirs(outdir, exist_ok=True)
    log("产物目录: %s" % outdir)

    cmd = [sys.executable, "-X", "utf8", LAUNCHER,
           "--kit", KIT, "--data-kit", DATA_KIT, "--game-root", GAME,
           "--seconds", str(a.seconds)]
    chain_log = open(os.path.join(outdir, "chain_stdout.txt"), "w", encoding="utf-8")
    log("起原封链: --seconds %d" % a.seconds)
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=chain_log, stderr=subprocess.STDOUT)

    # ★ 立刻把观察者交给 elevated agent（它在提权进程里 50ms 轮询抢早期句柄）
    watcher = [sys.executable, "-I", WATCHER, outdir,
               "--full-at", str(a.full_at), "--full-mb", str(a.full_mb),
               "--sample-secs", str(a.sample_secs), "--wait", "180"]
    log("经 agent 起观察者（抢早期句柄 + 定点采样 + 分块全量转储）")
    w = agent_run(watcher, timeout=900)
    log("观察者 ok=%s rc=%s" % (w.get("ok"), w.get("rc")))
    if w.get("stdout"):
        with open(os.path.join(outdir, "watcher_stdout.txt"), "w", encoding="utf-8") as f:
            f.write(w["stdout"])
        for ln in w["stdout"].strip().splitlines()[:12]:
            log("  | " + ln)
    if w.get("stderr"):
        print("[watcher stderr] " + w["stderr"], file=sys.stderr)

    rc = p.wait()
    chain_log.close()
    log("链结束 rc=%s" % rc)
    mem = os.path.join(outdir, "mem")
    n = len(os.listdir(mem)) if os.path.isdir(mem) else 0
    tot = 0
    if n:
        tot = sum(os.path.getsize(os.path.join(mem, f)) for f in os.listdir(mem))
    log("转储区域 %d 个, %.1f MB ; 采样 -> %s" % (n, tot / 1048576,
                                                 os.path.join(outdir, "probe.txt")))
    log("收尾: 停残留")
    kill_leftovers()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
