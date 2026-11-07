#!/usr/bin/env python3
"""138 对照实验：**在 run-local 副本里删掉 ready_push.on**，其余完全同链。

为什么不用 run_frozen_chain_capture_once.py：它内部会重建 kit 且无法插入删除点。
本脚本自己复刻它的准备工作（复制 CORE+数据目录+改 GAME_ROOT+单次重试），
唯一差异 = 复制后 `unlink(ready_push.on)`。源 kit 一字不动。

用法:
  python -X utf8 tools/dyn138_nopush_launch.py --prepare-only   # 只准备不启动
  python -X utf8 tools\dyn138_nopush_launch.py --seconds 360
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
RUNS = os.path.join(ROOT, "run_codol_001", "runs")
KIT = os.path.join(ROOT, "GOLDEN-LOBBY-001", "REF_LOBBY_KIT")
DATA_KIT = os.path.join(ROOT, "CODOL_VERIFIED_GOLDEN_20261019")
GAME = os.path.join(ROOT, "COD OL")
AGENT_CFG = os.path.join(ROOT, "CODOLServer", "logs", "elevated_agent.json")
PROBE = os.path.join(ROOT, "tools", "dyn138_create_room_probe.py")
CLEAN = os.path.join(ROOT, "tools", "dyn138_clean.py")
TARGET = "codoMP_client_shipRetail.exe"

CORE = [
    "run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
    "codol_crypto.py", "write_dwauth.py", "make_local_ca.ps1", "battle_server.py",
    "battle_selftest.py", "match_state_observer.py", "marketplace_store.py",
    "_rsa.txt", "_leaf2.cer", "_ca.pem", "_ca.cer", "_leaf2.key", "_leaf2_chain.pem",
    "lobby_spec.txt", "tas_spec.txt", "patch_spec.txt", "late_spec.txt",
    "player-account.json", "marketplace-inventory.json", "marketplace-catalog.json",
    "marketplace-catalog-merged.json", "marketplace-catalog-client.json",
    "playlist_resolver.py", "dynamic_gamestate.py", "codol_battle_server.exe",
    "firingrange-gamestate.bin",
    # 开关文件（.on）—— 注意 ready_push.on 稍后会被删
    "playlists-include-pve.on", "ready_push.on", "mirror_predicted.on",
    "client_movement.on", "omit_viewangles.on",
    "marketplace-skus.on", "marketplace-skus-allow-unsafe.on",
    "marketplace-skus-count.txt", "marketplace-currency-lenient.on",
    "catalog-include-sku-table.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
]


def log(s):
    print("[nopush] " + s, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def verify_golden():
    m = os.path.join(KIT, "_golden_hashes.json")
    if not os.path.isfile(m):
        return ["missing manifest"]
    data = json.load(open(m, encoding="utf-8"))
    bad = []
    for name in sorted(data):
        want = data[name]
        f = os.path.join(KIT, name)
        if not os.path.isfile(f):
            bad.append(name + ":missing")
        elif os.path.getsize(f) != int(want["size"]):
            bad.append(name + ":size")
        elif sha(f) != str(want["sha256"]).upper():
            bad.append(name + ":sha256")
    return bad


def pids():
    o = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace").stdout
    out = []
    for ln in o.splitlines():
        c = [x.strip('"') for x in ln.split('","')]
        if c and c[0].casefold() == TARGET.casefold():
            try:
                out.append(int(c[1].replace(",", "")))
            except (IndexError, ValueError):
                pass
    return out


def free(host, port):
    try:
        with socket.create_connection((host, port), timeout=.4):
            return True
    except OSError:
        return False


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
        return {"ok": False, "error": repr(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=360)
    ap.add_argument("--prepare-only", action="store_true")
    a = ap.parse_args()

    bad = verify_golden()
    if bad:
        print("protected baseline changed: " + ", ".join(bad), file=sys.stderr)
        return 2
    log("受保护基线 OK")

    ag = json.load(open(AGENT_CFG, encoding="utf-8"))
    log("agent pid=%s debug=%s" % (ag.get("pid"), ag.get("debug_privilege")))
    if not ag.get("debug_privilege"):
        return 2

    # 提权清理 + 等端口释放
    r = agent_run([sys.executable, "-I", CLEAN, "--keep", str(ag["pid"])], timeout=180)
    log("提权清理: %s" % (r.get("stdout") or r.get("error") or "").strip())
    time.sleep(3)
    for _ in range(15):
        if not free("127.0.0.1", 3074) and not free("127.0.0.2", 3074):
            break
        time.sleep(1)
    if free("127.0.0.1", 3074) or free("127.0.0.2", 3074):
        log("!! 3074 仍被占用，中止")
        return 2
    if pids():
        log("!! 仍有客户端进程 %s，中止" % pids())
        return 2

    # ---- 造 run-local kit ----
    run = os.path.join(RUNS, "NOPUSH_" + time.strftime("%Y%m%d_%H%M%S"))
    work = os.path.join(run, "kit")
    os.makedirs(work, exist_ok=True)
    copied, missing = 0, []
    for n in CORE:
        s = os.path.join(KIT, n)
        if not os.path.isfile(s):
            s2 = os.path.join(ROOT, "REF_LOBBY_KIT", n)
            s = s2 if os.path.isfile(s2) else s
        if not os.path.isfile(s):
            missing.append(n)
            continue
        shutil.copyfile(s, os.path.join(work, n))
        copied += 1
    for d in ("publisher_files", "player_profiles", "user_files", "mkt_assets", "sku_arrays"):
        sd = os.path.join(DATA_KIT, d)
        if not os.path.isdir(sd):
            raise SystemExit("缺数据目录 " + sd)
        shutil.copytree(sd, os.path.join(work, d))
    log("kit 复制 %d 文件 ; 缺=%s" % (copied, missing or "无"))

    # ★★ 唯一差异：删掉 ready_push.on
    flag = os.path.join(work, "ready_push.on")
    had = os.path.isfile(flag)
    if had:
        os.remove(flag)
    log("★★ ready_push.on 存在=%s -> 已删除=%s" % (had, not os.path.isfile(flag)))

    # run_all.py GAME_ROOT -> 本体
    la = os.path.join(work, "run_all.py")
    lines = open(la, encoding="utf-8").read().splitlines()
    hit = False
    for i, ln in enumerate(lines):
        if ln.startswith("GAME_ROOT ="):
            lines[i] = 'GAME_ROOT = r"%s"' % GAME
            hit = True
            break
    if not hit:
        raise SystemExit("run_all.py 无 GAME_ROOT")
    open(la, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    # nt10.py 单次重试
    nt = os.path.join(work, "nt10.py")
    t = open(nt, encoding="utf-8").read()
    t2 = t.replace("for _try in range(1, 6):", "for _try in range(1, 2):", 1)
    open(nt, "w", encoding="utf-8", newline="\n").write(t2)
    log("nt10 单次重试=%s" % (t2 != t))

    json.dump({"kit": KIT, "run": run, "ready_push_on_removed": had,
               "seconds": a.seconds, "copied": copied, "missing": missing},
              open(os.path.join(run, "preflight.json"), "w", encoding="utf-8"), indent=2)
    if a.prepare_only:
        log("prepare-only 完成: %s" % run)
        return 0

    # ---- 起探针（提权）----
    probe_out = os.path.join(run, "probe_tcp_mem.txt")
    th = threading.Thread(target=lambda: agent_run(
        [sys.executable, "-I", PROBE, probe_out, "--secs", str(a.seconds + 60)],
        timeout=a.seconds + 240), daemon=True)
    th.start()
    log("探针已起（提权只读）-> %s" % probe_out)
    time.sleep(1.5)

    # ---- 起链 ----
    token = os.path.join(RUNS, ".frozen_launch_used")
    open(token, "w").write("nopush\n")   # 占位，防止外部启动器并发
    cmd = [sys.executable, "-X", "utf8", os.path.join(work, "run_all.py"),
           "--secs", str(a.seconds), "--out", os.path.join(run, "chain.txt"),
           "--retries", "1"]
    log("起链: %s" % " ".join(cmd[2:]))
    r = agent_run(cmd, timeout=a.seconds + 180)
    log("链 rc=%s ok=%s" % (r.get("rc"), r.get("ok")))
    if r.get("stdout"):
        open(os.path.join(run, "chain_stdout.txt"), "w", encoding="utf-8").write(r["stdout"])
        tail = r["stdout"].strip().splitlines()[-12:]
        for ln in tail:
            log("  | " + ln)
    if r.get("stderr"):
        open(os.path.join(run, "chain_stderr.txt"), "w", encoding="utf-8").write(r["stderr"])

    # 收尾清理
    time.sleep(1)
    agent_run([sys.executable, "-I", CLEAN, "--keep", str(ag["pid"])], timeout=180)
    log("完成 run=%s" % run)
    log("对比要点：lobby_srv.log 里 11/4 是否还有『已回显频道推送+game start』；是否还有 ConnectionReset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
