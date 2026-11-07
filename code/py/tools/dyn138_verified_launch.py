#!/usr/bin/env python3
"""138c: 用 **VERIFIED 版 lobby_server.py** 跑一次实机（链原封，仅换实现版本）。

与之前唯一差异：
  - 源的 lobby_server.py 来自 CODOL_VERIFIED_GOLDEN_20261019（1575 行，含全部修复）
  - 其余仍从 GOLDEN kit 取（run_all/nt10/crypto/证书等）
  - 复制后**打印 lobby_server.py 的 SHA256 以自证版本**（教训：实验前必须 hash+报版本）
  - 仍生成 run-local 副本；受保护目录只读
用法:
  python -X utf8 tools/dyn138_verified_launch.py --prepare-only
  python -X utf8 tools\dn138_verified_launch.py --seconds 360
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
VER = os.path.join(ROOT, "CODOL_VERIFIED_GOLDEN_20261019")
GAME = os.path.join(ROOT, "COD OL")
AGENT_CFG = os.path.join(ROOT, "CODOLServer", "logs", "elevated_agent.json")
PROBE = os.path.join(ROOT, "tools", "dyn138_create_room_probe.py")
CLEAN = os.path.join(ROOT, "tools", "dyn138_clean.py")
TARGET = "codoMP_client_shipRetail.exe"

# ★ 这些文件用 VERIFIED 版（含修复）
FROM_VERIFIED = {"lobby_server.py", "codol_crypto.py", "_sku_schema_as.py",
                 "marketplace_store.py", "market_skus.py", "write_dwauth.py"}

CORE = [
    "run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
    "codol_crypto.py", "write_dwauth.py", "make_local_ca.ps1", "battle_server.py",
    "battle_selftest.py", "match_state_observer.py", "marketplace_store.py",
    "market_skus.py", "_sku_schema_as.py",
    "_rsa.txt", "_leaf2.cer", "_ca.pem", "_ca.cer", "_leaf2.key", "_leaf2_chain.pem",
    "lobby_spec.txt", "tas_spec.txt", "patch_spec.txt", "late_spec.txt",
    "player-account.json", "marketplace-inventory.json", "marketplace-catalog.json",
    "marketplace-catalog-merged.json", "marketplace-catalog-client.json",
    "playlist_resolver.py", "dynamic_gamestate.py", "codol_battle_server.exe",
    "firingrange-gamestate.bin",
    "playlists-include-pve.on", "ready_push.on", "mirror_predicted.on",
    "client_movement.on", "omit_viewangles.on",
    "marketplace-skus.on", "marketplace-skus-allow-unsafe.on",
    "marketplace-skus-count.txt", "marketplace-currency-lenient.on",
    "catalog-include-sku-table.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
]


def log(s):
    print("[ver] " + s, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


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

    # ★★ 版本自证（教训：实验前必须 hash + 报版本）
    log("=== 版本自证 ===")
    for n in ("lobby_server.py", "codol_crypto.py"):
        g = os.path.join(KIT, n)
        v = os.path.join(VER, n)
        log("  GOLDEN   %-20s %s" % (n, sha(g)[:16] if os.path.isfile(g) else "缺"))
        log("  VERIFIED %-20s %s" % (n, sha(v)[:16] if os.path.isfile(v) else "缺"))
    if not os.path.isfile(os.path.join(VER, "lobby_server.py")):
        log("!! VERIFIED 缺 lobby_server.py，中止")
        return 2

    ag = json.load(open(AGENT_CFG, encoding="utf-8"))
    log("agent pid=%s debug=%s" % (ag.get("pid"), ag.get("debug_privilege")))
    if not ag.get("debug_privilege"):
        return 2

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
        log("!! 仍有客户端 %s，中止" % pids())
        return 2

    run = os.path.join(RUNS, "VER_" + time.strftime("%Y%m%d_%H%M%S"))
    work = os.path.join(run, "kit")
    os.makedirs(work, exist_ok=True)
    copied, srcmap = 0, {}
    for n in CORE:
        cands = []
        if n in FROM_VERIFIED:
            cands.append(os.path.join(VER, n))
        cands += [os.path.join(KIT, n), os.path.join(ROOT, "REF_LOBBY_KIT", n),
                  os.path.join(VER, n)]
        src = next((c for c in cands if os.path.isfile(c)), None)
        if not src:
            srcmap[n] = "缺"
            continue
        shutil.copyfile(src, os.path.join(work, n))
        srcmap[n] = "VERIFIED" if src.startswith(VER) else "GOLDEN"
        copied += 1
    for d in ("publisher_files", "player_profiles", "user_files", "mkt_assets", "sku_arrays"):
        sd = os.path.join(VER, d)
        if not os.path.isdir(sd):
            sd = os.path.join(KIT, d)
        if not os.path.isdir(sd):
            raise SystemExit("缺数据目录 " + d)
        shutil.copytree(sd, os.path.join(work, d))
    log("kit 复制 %d 文件" % copied)
    log("★ 关键文件来源: lobby_server.py=%s codol_crypto.py=%s"
        % (srcmap.get("lobby_server.py"), srcmap.get("codol_crypto.py")))
    log("★ 实际写入的 lobby_server.py SHA256 = %s"
        % sha(os.path.join(work, "lobby_server.py"))[:16])
    log("★ 行数 = %d" % len(open(os.path.join(work, "lobby_server.py"),
                                encoding="utf-8", errors="replace").read().splitlines()))

    # 确认 VERIFIED 的修复真的在
    txt = open(os.path.join(work, "lobby_server.py"), encoding="utf-8",
               errors="replace").read()
    for feat, needle in (("build_startgame_payload", "def build_startgame_payload"),
                         ("build_room_push", "def build_room_push"),
                         ("seq用out_seq", "_pseq = out_seq"),
                         ("memberCount=1", "ob.u32(1); ob.u32(1)")):
        log("  %-24s %s" % (feat, "✓" if needle in txt else "✗ 缺失!"))

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

    nt = os.path.join(work, "nt10.py")
    t = open(nt, encoding="utf-8").read()
    t2 = t.replace("for _try in range(1, 6):", "for _try in range(1, 2):", 1)
    open(nt, "w", encoding="utf-8", newline="\n").write(t2)

    json.dump({"run": run, "seconds": a.seconds, "srcmap": srcmap,
               "lobby_sha": sha(os.path.join(work, "lobby_server.py")),
               "lines": len(txt.splitlines())},
              open(os.path.join(run, "preflight.json"), "w", encoding="utf-8"), indent=2)
    if a.prepare_only:
        log("prepare-only 完成: %s" % run)
        return 0

    probe_out = os.path.join(run, "probe_tcp_mem.txt")
    threading.Thread(target=lambda: agent_run(
        [sys.executable, "-I", PROBE, probe_out, "--secs", str(a.seconds + 60)],
        timeout=a.seconds + 240), daemon=True).start()
    log("探针已起 -> %s" % probe_out)
    time.sleep(1.5)

    open(os.path.join(RUNS, ".frozen_launch_used"), "w").write("verified\n")
    cmd = [sys.executable, "-X", "utf8", os.path.join(work, "run_all.py"),
           "--secs", str(a.seconds), "--out", os.path.join(run, "chain.txt"),
           "--retries", "1"]
    log("起链(VERIFIED lobby_server)")
    r = agent_run(cmd, timeout=a.seconds + 180)
    log("链 rc=%s ok=%s" % (r.get("rc"), r.get("ok")))
    if r.get("stdout"):
        open(os.path.join(run, "chain_stdout.txt"), "w", encoding="utf-8").write(r["stdout"])
        for ln in r["stdout"].strip().splitlines()[-14:]:
            log("  | " + ln)
    if r.get("stderr"):
        open(os.path.join(run, "chain_stderr.txt"), "w", encoding="utf-8").write(r["stderr"])

    time.sleep(1)
    agent_run([sys.executable, "-I", CLEAN, "--keep", str(ag["pid"])], timeout=180)
    log("完成 run=%s" % run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
