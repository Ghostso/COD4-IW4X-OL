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
DEFAULT_GAME = ROOT / "run_codol_001" / "sandbox_ifs1_20260923"
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
    "firingrange-session.enabled", "firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH",
    "playlists-include-pve.on", "ready_push.on", "mirror_predicted.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
    "marketplace-currency-lenient.on", "catalog-include-sku-table.on",
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
    for name in ("tas_off.flag", "poke_off.flag"):
        if (PROTECTED_ROOT / name).exists():
            bad.append(name + ":runtime-state")
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
    ap = argparse.ArgumentParser(description="Launch the frozen CODOL chain exactly once")
    ap.add_argument("--kit", type=Path, default=DEFAULT_KIT)
    ap.add_argument("--game-root", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--seconds", type=int, default=90)
    ap.add_argument("--out", default="chain.txt")
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--authorize-next-launch", action="store_true")
    a = ap.parse_args()
    kit = a.kit.resolve()
    game = a.game_root.resolve()
    manifest_path = kit / "_run_once_hashes.json"
    protected_bad = verify_protected_baseline()
    if protected_bad:
        print("protected baseline changed: " + ", ".join(protected_bad), file=sys.stderr)
        return 2
    if a.verify_only:
        print("protected baseline: OK")
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
    for n in CORE:
        if (kit / n).is_file(): shutil.copy2(kit / n, work / n)
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
           "--secs", str(a.seconds), "--out", str(run / a.out), "--retries", "1"]
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
