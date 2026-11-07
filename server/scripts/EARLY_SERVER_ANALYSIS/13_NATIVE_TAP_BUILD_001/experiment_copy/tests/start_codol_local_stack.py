"""Start a persistent, loopback-only 1.1.1.13 stack for manual launcher testing.

Run from the lobby virtual environment. All runtime state stays in the copied
client directory under %%TEMP%%. Stop only the recorded PIDs when finished.
"""

import argparse
import configparser
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import sysconfig
import time
from urllib.request import urlopen


def rcon_status(port, password):
    request = b'\xff\xff\xff\xffrcon "' + password.encode("ascii") + b'" sh1x_status'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.5)
        sock.sendto(request, ("127.0.0.1", port))
        try:
            return sock.recvfrom(4096)[0].decode("ascii", errors="replace")
        except (socket.timeout, ConnectionResetError):
            return ""


def wait_for(label, predicate, processes, timeout):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        for name, process in processes.items():
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited while waiting for {label}: {process.returncode}")
        if predicate():
            return
        time.sleep(0.4)
    raise RuntimeError(f"timed out waiting for {label}")


def main():
    try:
        from Crypto.Cipher import DES3  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("run this stack with the lobby virtual environment (pycryptodome required)") from exc
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--client-root", type=Path, required=True)
    ap.add_argument("--lobby", type=Path, required=True)
    ap.add_argument("--launcher", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--port", type=int, default=17733)
    args = ap.parse_args()
    install, client_root, lobby, launcher, exe = (
        p.resolve() for p in (args.install, args.client_root, args.lobby, args.launcher, args.exe)
    )
    if not client_root.is_relative_to(Path(os.environ["TEMP"]).resolve()) or not client_root.name.startswith("codol-11113-"):
        ap.error("client-root must be an isolated codol-11113-* copy under TEMP")
    sandbox_lobby = client_root / "lobby"
    launcher_exe = client_root / "TCLS" / "CODOLLauncher" / "bin" / "CODOLLauncher.exe"
    for required in (install / "main", client_root / "C1.exe", client_root / "C1.dll",
                     sandbox_lobby / "dw-capture.py", launcher_exe, launcher / "server" / "mock_server.py", exe):
        if not required.exists():
            ap.error(f"missing exact-build input: {required}")
    pid_file = client_root / "local-stack-pids.json"
    if pid_file.exists():
        ap.error(f"existing stack PID record; inspect and stop before restarting: {pid_file}")
    cfg = configparser.ConfigParser()
    cfg.read(launcher_exe.with_name("launcher.ini"), encoding="utf-8-sig")
    if cfg.get("server", "url", fallback="") != "http://127.0.0.1:8087":
        ap.error("sandbox launcher is not configured for local mock backend")
    if cfg.get("game", "exe", fallback="").lower() != str(client_root / "C1.exe").lower():
        ap.error("sandbox launcher is not configured for copied exact client")
    for port in (3074, 8087):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                ap.error(f"TCP port {port} already in use")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("127.0.0.1", args.port))
        except OSError:
            ap.error(f"UDP port {args.port} already in use")

    state = sandbox_lobby
    key = state / "securitykey.bin"
    if not key.exists():
        key.write_bytes(secrets.token_bytes(16))
    password_file = state / "native_server_rcon.txt"
    if not password_file.exists():
        password_file.write_text(secrets.token_hex(16) + "\n", encoding="ascii")
    password = password_file.read_text(encoding="ascii").strip()
    home = client_root / "server-home"
    (home / "main").mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import codol_package
    codol_package.build_pack(str(home / "main" / codol_package.PACK))
    logs = client_root / "local-stack-logs"
    logs.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(CODOL_STATE_DIR=str(state), CODOL_ADMISSION="0", CODOL_ADMISSION_PORT="0",
               CODOL_INSTANCES="0", CODOL_MM_HOST_PORT=str(args.port),
               CODOL_MATCH_RCON_HOST="127.0.0.1", CODOL_MATCH_RCON_PORT=str(args.port))
    # The base interpreter avoids the Windows venv redirector's untracked
    # child PID. Keep the virtual environment's packages available to it.
    env["PYTHONPATH"] = sysconfig.get_paths()["purelib"]
    crypto_probe = subprocess.run(
        [sys._base_executable, "-c", "from Crypto.Cipher import DES3"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )
    if crypto_probe.returncode != 0:
        raise RuntimeError("lobby interpreter cannot import pycryptodome")
    scripts = Path(__file__).resolve().parent.parent / "bin" / "home" / "codol_rawfiles"
    processes = {}
    handles = []

    def start(name, command, cwd):
        out = (logs / f"{name}.stdout").open("wb")
        err = (logs / f"{name}.stderr").open("wb")
        handles.extend((out, err))
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
        processes[name] = process
        return process

    try:
        start("backend", [sys._base_executable, str(launcher / "server" / "mock_server.py"),
                          "--host", "127.0.0.1", "--port", "8087"], launcher)
        def backend_ready():
            try:
                return urlopen("http://127.0.0.1:8087/api/v1/launcher/version", timeout=1).status == 200
            except OSError:
                return False
        wait_for("launcher backend", backend_ready, processes, 15)
        start("lobby", [sys._base_executable, str(sandbox_lobby / "dw-capture.py"),
                        "--host", "127.0.0.1", "--port", "3074", "--no-alt", "--respond",
                        "--log", str(state / "dw-capture.log")], sandbox_lobby)
        def lobby_listening():
            with socket.socket() as sock:
                sock.settimeout(0.3)
                return sock.connect_ex(("127.0.0.1", 3074)) == 0
        wait_for("lobby TCP", lobby_listening, processes, 15)
        command = [str(exe), "+set", "dedicated", "2", "+set", "fs_basepath", str(install),
                   "+set", "fs_homepath", str(home), "+set", "codol_clientExe", str(client_root / "C1.exe"),
                   "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(args.port),
                   "+set", "rcon_password", password, "+set", "logfile", "2",
                   "+set", "codol_scriptPath", str(scripts), "+set", "codol_scriptOverlay", str(scripts),
                   "+set", "codol_scriptNativeOverlay", str(scripts),
                   "+set", "codol_securityKeyPath", str(key), "+set", "codol_admissionRequired", "0",
                   "+set", "codol_profilePath", str(sandbox_lobby / "resources"),
                   "+set", "codol_zoneType", "mp", "+set", "codol_sessionMap", "mp_rust",
                   "+set", "g_gametype", "dm", "+set", "scr_codol_bots", "12",
                   "+set", "scr_dm_scorelimit", "0",
                   "+set", "scr_dm_timelimit", "0",
                   "+set", "sv_botDifficulty", "recruit",
                   "+set", "developer", "1", "+map", "mp_rust"]
        if len(subprocess.list2cmdline(command[1:])) >= 8192:
            raise RuntimeError("server command exceeds supported length")
        start("server", command, exe.parent)
        wait_for("native mp_rust/dm", lambda: "map=mp_rust" in rcon_status(args.port, password) and
                 "gametype=dm" in rcon_status(args.port, password), processes, 90)
        pid_file.write_text(json.dumps({name: p.pid for name, p in processes.items()}, indent=2) + "\n", encoding="ascii")
        print(f"READY backend=http://127.0.0.1:8087 lobby=127.0.0.1:3074 server=127.0.0.1:{args.port}")
        print(f"PIDs: {pid_file}")
        print(f"Logs: {logs}")
        print(f"Launcher: {launcher_exe}")
    except Exception:
        for process in reversed(list(processes.values())):
            if process.poll() is None:
                process.terminate()
        raise
    finally:
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
