# -*- coding: utf-8 -*-
"""Single-shot launcher for the verified frozen CODOL chain.

Design guarantees:
  * The source kit is verified against a JSON manifest and never rewritten.
  * Each invocation gets exactly one immutable run id and isolated output dir.
  * The game/client is started at most once; no automatic relaunch.
  * Generated config, logs, flags and snapshots stay under runs/<run-id>/.
  * A failed launch returns nonzero and leaves the source kit untouched.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, socket, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KIT = ROOT / "CODOL_VERIFIED_GOLDEN_20261019"
DEFAULT_GAME = ROOT / "COD OL" if (ROOT / "COD OL").is_dir() else (ROOT.parent / "COD OL")
# ★★ 2026-10-27 用户明确: **不得使用沙箱**。
#   本体的全部重要推进都是在本体上做的; 沙箱是残缺副本 ——
#     · 本体 3095 个文件 / 24.7 GB    vs   沙箱 129 个文件 / 0.4 GB
#     · 本体有 codoMP_client_shipRetail.exe.local\ 和 ...Base.dll.local\,
#       里面各有一份 **不同的** Base.dll (sha256 3D2B338D…),
#       而根目录那份是 EF75220D…; Windows DLL 重定向会优先加载 .local 里的,
#       沙箱没有 .local ⇒ 沙箱里跑的 Base.dll 与本体根本不是同一份。
#   ⇒ 实验必须在本体上跑, 沙箱结果一律无效。
RUNS = ROOT / "run_codol_001" / "runs"
TARGET = "codoMP_client_shipRetail.exe"
CORE = [
    "run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
    "codol_crypto.py", "write_dwauth.py", "make_local_ca.ps1", "battle_server.py",
    "_rsa.txt", "_leaf2.cer", "_ca.pem", "_ca.cer", "_leaf2.key",
    "_leaf2_chain.pem", "lobby_spec.txt", "tas_spec.txt", "patch_spec.txt",
    "late_spec.txt", "player-account.json", "marketplace-inventory.json",
    "marketplace-catalog-merged.json", "marketplace-catalog-client.json",
    "marketplace-catalog.json", "firingrange-gamestate.bin",
    "firingrange-session.enabled", "firingrange-battle.enabled",
    "firingrange-booking-push.enabled",
    "firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH",
    "playlists-include-pve.on", "ready_push.on", "mirror_predicted.on",
    "lobbytable-scan.on", "roomprobe.on",
    "client_movement.on", "omit_viewangles.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
    "marketplace-currency-lenient.on", "catalog-include-sku-table.on",
    "playlist_resolver.py", "dynamic_gamestate.py", "codol_battle_server.exe",
    # ★ 2026-10-28: nt10.py 在观测阶段 `import match_state_observer`。此前
    #   prepared_once.py 里有一行显式 copy，但本文件的 CORE 白名单没有它，
    #   导致 runtime_kit 缺文件 -> nt10 启动后崩在 ModuleNotFoundError，
    #   客户端被拉起来却立即无人接管（实测 run ONCE_20261028_212339）。
    "match_state_observer.py",
    # 旧战斗服实现默认不启用; 需要对照时把对应开关文件放进 kit 即可。
    "battle-legacy-py.enabled", "battle-legacy-c.enabled",
    "codol_battle_server.legacy.exe", "battle_server.legacy.py",
    # SKU 目录页下发所需的模块与开关 (pilot30: 30 条 30000 段名片)
    # ★ 2026-10-30: marketplace_store.py 此前**从未**在白名单里, 于是
    #   `import marketplace_store as ms` 失败 -> ms=None -> 80/70、80/107…
    #   全部落到兜底空应答, 商城目录/库存/购买分支整条不执行
    #   (实测 run ONCE_20261030_204133 的 7 个目录 task 全部空应答)。
    "marketplace_store.py",
    "market_skus.py", "_sku_schema_as.py",
    "marketplace-skus.on", "marketplace-skus-allow-unsafe.on",
    "marketplace-skus-count.txt",
]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def pids() -> list[int]:
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace")
    out = []
    for line in r.stdout.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if c and c[0].casefold() == TARGET.casefold():
            try: out.append(int(c[1].replace(",", "")))
            except (IndexError, ValueError): pass
    return out

def free(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=.4): return True
    except OSError: return False


PROTECTED_ROOT = ROOT / "REF_LOBBY_KIT"
PROTECTED_MANIFEST = PROTECTED_ROOT / "_golden_hashes.json"

def verify_protected_baseline() -> list[str]:
    if not PROTECTED_MANIFEST.is_file():
        return ["missing REF_LOBBY_KIT/_golden_hashes.json"]
    data = json.loads(PROTECTED_MANIFEST.read_text(encoding="utf-8"))
    # Marketplace data is a business-only module.  It cannot change IIPS,
    # Auth, or Lobby startup behavior, so it is never allowed to block a
    # launch-chain health check.
    launch_core = {
        "run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
        "codol_crypto.py", "make_local_ca.ps1",
    }
    bad = []
    for name in sorted(launch_core):
        want = data.get(name)
        if not want:
            bad.append(name + ":manifest-missing")
            continue
        f = PROTECTED_ROOT / name
        if not f.is_file():
            bad.append(name + ":missing")
        elif f.stat().st_size != int(want["size"]):
            bad.append(name + ":size")
        elif sha(f) != str(want["sha256"]).upper():
            bad.append(name + ":sha256")
    # These two zero-byte isolation flags are part of the verified baseline:
    # they disable TAS injection and lobby-global pokes without changing the
    # launch chain. Accept them only when present and empty; any other state
    # is still a runtime-state violation.
    for name in ("tas_off.flag", "poke_off.flag"):
        f = PROTECTED_ROOT / name
        if f.exists() and (not f.is_file() or f.stat().st_size != 0):
            bad.append(name + ":runtime-state")
    return bad

# ★ 2026-11-03 (卷 271): 防止「校验对象 ≠ 执行对象」再次发生。
#
# 历史事故: DEFAULT_KIT 指向 `CODOL_VERIFIED_GOLDEN_20261019`, 而 PROTECTED_ROOT 指向
# `REF_LOBBY_KIT`。两者分叉(lobby_server.py 差 11.7KB / nt10.py 差 882B /
# battle_server.py 差 1.2KB)后, `verify_protected_baseline()` 长期**全绿**,
# 但它保护的是一套**根本没在跑的代码**。
# 见 `_byte_papers/papers/lobby/271_统一固化启动链_*.md`。
#
# 本链把 `REF_LOBBY_KIT` 建成 kit 的镜像; 这里显式断言二者对 launch_core 逐字节一致,
# 一旦再次脱钩就当场失败(而不是继续绿着)。
LAUNCH_CORE = ("run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
               "codol_crypto.py", "make_local_ca.ps1")

def verify_kit_matches_protected(kit: Path) -> list[str]:
    bad = []
    for name in LAUNCH_CORE:
        a = PROTECTED_ROOT / name
        b = kit / name
        if not a.is_file():
            bad.append(name + ":protected-missing")
        elif not b.is_file():
            bad.append(name + ":kit-missing")
        elif sha(a) != sha(b):
            bad.append(name + ":kit!=protected(校验一套/跑另一套)")
    return bad

def make_run_id() -> Path:
    token = RUNS / ".frozen_launch_used"
    if token.exists():
        raise SystemExit("refusing launch: the single launch token was already consumed; "
                         "remove it only after an explicit baseline reset")
    run = RUNS / ("ONCE_" + time.strftime("%Y%m%d_%H%M%S"))
    run.mkdir(parents=True, exist_ok=True)
    token.write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z") + "`n", encoding="utf-8")
    return run

def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Launch the frozen CODOL chain exactly once")
    ap.add_argument("--kit", type=Path, default=DEFAULT_KIT)
    ap.add_argument("--game-root", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--seconds", type=int, default=90)
    ap.add_argument("--out", default="chain.txt")
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--authorize-next-launch", action="store_true")
    ap.add_argument("--allow-kit-divergence", action="store_true",
                    help="仅用于隔离实验 source kit；仍校验受保护基线")
    # ★ 2026-11-05: 观测用的 API hook 集透传给 run_all.py。
    #   默认里**没有 WSASendTo/WSASend** —— 而 nt10 自己的注释写明"游戏 UDP 走 WSASendTo"，
    #   所以默认配置下**完全看不到游戏 socket 发去哪**(日志里只有遥测目标)。
    #   排查"客户端到底往哪发 getchallenge"时必须带上它们。
    ap.add_argument("--apis",
                    default="OpenFileMappingW,CreateFileMappingW,MapViewOfFile,"
                            "connect,sendto,send,WSASend,WSASendTo,"
                            "WinHttpConnect,WinHttpOpenRequest,WinHttpSendRequest,z1,z2")
    a = ap.parse_args()
    kit = a.kit.resolve()
    game = a.game_root.resolve()
    manifest_path = kit / "_run_once_hashes.json"
    protected_bad = verify_protected_baseline()
    if protected_bad:
        print("protected baseline changed: " + ", ".join(protected_bad), file=sys.stderr)
        return 2
    mirror_bad = verify_kit_matches_protected(kit)
    if mirror_bad and not a.allow_kit_divergence:
        print("kit != protected mirror: " + ", ".join(mirror_bad), file=sys.stderr)
        return 3
    if mirror_bad:
        print("[isolated] kit divergence explicitly allowed: " + ", ".join(mirror_bad))
    if a.verify_only:
        print("protected baseline: OK")
        print("kit == protected mirror: OK")
        return 0
    if a.authorize_next_launch:
        token = RUNS / ".frozen_launch_used"
        if token.exists():
            token.unlink()
        print("single launch authorized")
        return 0
    if a.write_manifest:
        manifest = {n: {"size": (kit / n).stat().st_size, "sha256": sha(kit / n)}
                    for n in CORE if (kit / n).is_file()}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(manifest_path)
        return 0
    if not manifest_path.is_file():
        print("missing baseline manifest; run --write-manifest from a verified good kit", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad = []
    for n, want in manifest.items():
        p = kit / n
        if not p.is_file() or p.stat().st_size != want["size"] or sha(p) != want["sha256"]:
            bad.append(n)
    if bad:
        print("refusing launch: source kit differs from baseline: " + ", ".join(bad), file=sys.stderr)
        return 2
    existing = pids()
    if existing:
        print("refusing launch: existing client pids=" + ",".join(map(str, existing)), file=sys.stderr)
        return 2
    if free("127.0.0.1", 3074) or free("127.0.0.2", 3074):
        print("refusing launch: a 3074 listener already exists", file=sys.stderr)
        return 2
    run = make_run_id()
    work = run / "kit"
    work.mkdir()
    skipped_core = []
    for n in CORE:
        if (kit / n).is_file():
            shutil.copy2(kit / n, work / n)
        else:
            skipped_core.append(n)
    # ★ 2026-11-03 (卷 271/272): 缺文件此前是**静默跳过** —— golden 缺 market_skus.py 时,
    #   `import market_skus` 失败 -> market_skus=None -> 商城整条链退化成"回空页",
    #   而日志里不留一行。现在显式列出, 并落盘备查。
    #   注意: CORE 里有一部分条目本链**根本不 import**(如 playlist_resolver / dynamic_gamestate /
    #   match_state_observer —— 已机械核对: 0 处 import、0 处动态导入), 它们的缺席无害。
    if skipped_core:
        print("[!] CORE 白名单里 kit 缺失 %d 项(已跳过): %s"
              % (len(skipped_core), ", ".join(skipped_core)))
        (work / "_core_skipped.txt").write_text("\n".join(skipped_core) + "\n", encoding="utf-8")
    # Business data required after the IIPS/Auth gate. The frozen source kit
    # omitted these directories; that omission causes the documented
    # EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE dialog. They stay in the isolated run.
    data_manifest = {}
    for dirname in ("publisher_files", "player_profiles", "user_files", "mkt_assets", "sku_arrays"):
        src_dir = kit / dirname
        dst_dir = work / dirname
        if not src_dir.is_dir():
            raise SystemExit("source kit is missing required data directory: " + dirname)
        shutil.copytree(src_dir, dst_dir)
        data_manifest[dirname] = {
            p.name: {"size": p.stat().st_size, "sha256": sha(p), "source": str(p)}
            for p in sorted(src_dir.iterdir()) if p.is_file()
        }
    # Bind the copied launcher to this invocation's sandbox.  The master
    # launcher is never edited.
    launcher = work / "run_all.py"
    try:
        launcher.chmod(0o666)
    except OSError:
        pass
    text = launcher.read_text(encoding="utf-8")
    old_prefix = "GAME_ROOT ="
    lines = text.splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(old_prefix):
            lines[i] = 'GAME_ROOT = r"' + str(game) + '"'
            replaced = True
            break
    if not replaced:
        raise SystemExit("copied launcher has no GAME_ROOT assignment")
    launcher.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- 唯一战斗服: codol_battle_server.exe (当前 C 源码) ----
    # 术语: 本项目里「新 C 服 / 旧 C 服 / Python 服」**都指战斗服**, 不指大厅服。
    #   战斗服 = codol_battle_server.exe       (唯一启用, C 原生, UDP 28960)
    #   大厅服 = lobby_server.py               (Python, TCP 3074, 独立的另一个组件)
    # 旧实现 (battle_server.py / codol_battle_server.legacy.exe) 已废弃, 不再回退:
    # 它们的快照/基线语义落后于当前 C 源码(缺基线拒绝、视角字段、动态武器 ID),
    # 误用会静默复现已修的缺陷, 所以这里**不提供任何回退分支**。
    # 受保护的 master kit 里 run_all.py 指向旧 Python 骨架且不可写(归 SYSTEM 所有),
    # 故在**本 run 的隔离副本**上整体替换 start_battle_server 函数体。
    lt = launcher.read_text(encoding="utf-8")
    anchor = 'def start_battle_server(bind="0.0.0.0", port=28960):'
    start = lt.find(anchor)
    if start < 0:
        raise SystemExit("copied launcher: start_battle_server not found")
    tail = lt.find("\ndef ", start + len(anchor))
    if tail < 0:
        raise SystemExit("copied launcher: cannot find end of start_battle_server")
    new_fn = '''def start_battle_server(bind="0.0.0.0", port=28960):
    """战斗服(UDP)。唯一实现 = codol_battle_server.exe (当前 C 源码)。
    旧 Python 骨架与旧 C 构建已废弃, 无回退分支。"""
    path = os.path.join(ROOT, "codol_battle_server.exe")
    if not os.path.isfile(path):
        print("[!] 战斗服可执行文件缺失: %s" % path)
        return False
    print("=" * 70)
    print("[*] 起战斗服 UDP %s:%d : codol_battle_server.exe (唯一实现)" % (bind, port))
    print("=" * 70)
    out = os.path.join(ROOT, "_battle_out.txt")
    err = os.path.join(ROOT, "_battle_err.txt")
    argv = [path, "--bind", bind, "--port", str(port)]
    try:
        subprocess.Popen(argv, cwd=ROOT,
                         stdout=open(out, "w"), stderr=open(err, "w"),
                         stdin=subprocess.DEVNULL, creationflags=0x08000000)
    except Exception as e:
        print("      !! 起战斗服失败: %r" % (e,))
        return False
    time.sleep(1.5)
    logs = []
    for f in (os.path.join(ROOT, "battle_srv.log"), out, err):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip()
        except Exception:
            txt = ""
        if txt:
            logs.append(txt.splitlines()[-3:])
    print("      战斗服已拉起; 日志 battle_srv.log")
    for ls in logs:
        for ln in ls:
            print("      " + ln)
    return True

'''
    lt = lt[:start] + new_fn + lt[tail + 1:]
    launcher.chmod(0o666)
    launcher.write_text(lt, encoding="utf-8")

    # ---- 大厅服(lobby_server.py)不需要战斗服补丁 ----
    # 现在是唯一战斗服: lobby 的 maybe_start_battle_server 已直接拉
    # codol_battle_server.exe, 无回退分支。此处只做**断言**, 防止哪天 kit 被
    # 换回旧的 Python 骨架而静默退化。
    lobby = work / "lobby_server.py"
    lb = lobby.read_text(encoding="utf-8")
    if 'script = os.path.join(OUTDIR, "codol_battle_server.exe")' not in lb:
        raise SystemExit(
            "大厅服不是唯一战斗服配置: lobby_server.py 未直接拉起 "
            "codol_battle_server.exe (可能被换回了旧 Python 骨架)")
    if 'battle-legacy-py.enabled' in lb or 'battle-legacy-c.enabled' in lb:
        raise SystemExit(
            "大厅服里仍存在旧战斗服回退分支, 与「唯一战斗服」要求冲突")

    # The isolated copy is single-shot even though the protected reference
    # preserves its historical retry loop. Exactly one client launch is
    # therefore possible on any externally failed attempt.
    driver = work / "nt10.py"
    driver_text = driver.read_text(encoding="utf-8")
    old_retry = "for _try in range(1, 6):"
    if driver_text.count(old_retry) != 1:
        raise SystemExit("copied driver has an unexpected retry loop")
    driver_text = driver_text.replace(old_retry, "for _try in range(1, 2):", 1)
    driver.chmod(0o666)
    driver.write_text(driver_text, encoding="utf-8")
    (run / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run / "data_manifest.json").write_text(json.dumps(data_manifest, indent=2), encoding="utf-8")
    (run / "preflight.json").write_text(json.dumps({
        "source_kit": str(kit), "game_root": str(game), "client_pids": pids(),
        "start": time.time(), "seconds": a.seconds, "work_kit": str(work)
    }, indent=2), encoding="utf-8")
    # The documented chain must run inside the already elevated agent.  The
    # agent writes the exact child process return code back to this launcher.
    agent_state = ROOT / "CODOLServer" / "logs" / "elevated_agent.json"
    if not agent_state.is_file():
        print("refusing launch: elevated agent state is missing", file=sys.stderr)
        return 2
    try:
        agent = json.loads(agent_state.read_text(encoding="utf-8"))
        agent_pid = int(agent["pid"])
        agent_port = int(agent["port"])
        agent_token = str(agent["token"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("refusing launch: invalid elevated agent state: %s" % exc, file=sys.stderr)
        return 2
    if not agent.get("debug_privilege"):
        print("refusing launch: elevated agent did not enable its privilege", file=sys.stderr)
        return 2
    probe = subprocess.run(["tasklist", "/FI", "PID eq %d" % agent_pid, "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, errors="replace")
    if str(agent_pid) not in probe.stdout:
        print("refusing launch: elevated agent pid=%d is unavailable" % agent_pid,
              file=sys.stderr)
        return 2
    cmd = [sys.executable, "-X", "utf8", str(work / "run_all.py"),
           "--secs", str(a.seconds), "--out", str(run / a.out), "--retries", "1",
           "--apis", a.apis]
    print("[once] elevated agent pid=%d: %s" % (agent_pid, " ".join(cmd)), flush=True)
    request = json.dumps({"token": agent_token, "action": "run", "argv": cmd,
                          "cwd": str(work), "timeout": a.seconds + 120}).encode("utf-8") + b"\n"
    try:
        with socket.create_connection(("127.0.0.1", agent_port), timeout=a.seconds + 180) as s:
            s.sendall(request)
            payload = b""
            while not payload.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                payload += chunk
        response = json.loads(payload.decode("utf-8"))
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "elevated agent rejected launch")
        rc = int(response["rc"])
        if response.get("stdout"):
            print(response["stdout"], end="" if response["stdout"].endswith("\n") else "\n", flush=True)
        if response.get("stderr"):
            print(response["stderr"], end="" if response["stderr"].endswith("\n") else "\n",
                  file=sys.stderr, flush=True)
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        print("elevated launch failed: %s" % exc, file=sys.stderr)
        rc = 2
    post = {n: sha(work / n) for n in CORE if (work / n).is_file()}
    protected_after = verify_protected_baseline()
    (run / "postflight.json").write_text(json.dumps({
        "returncode": rc, "end": time.time(), "client_pids": pids(),
        "protected_baseline": protected_after,
        "protected_ok": not protected_after,
        "work_hashes": post
    }, indent=2), encoding="utf-8")
    print("[once] rc=%d run=%s" % (rc, run))
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
