"""Run a copied 1.1.1.13 C1, lobby, and native Windows server together.

This is an unattended startup/Ready-control check, not a human match-join test.
The client root must be a copy beneath the system temp directory; its INI and
log files are written during the run. Lobby source/resources are copied again
to an isolated directory, so no live career in the checkout is changed.
"""

import argparse
from pathlib import Path
import os
import secrets
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
import time


def unused_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def status(port, password):
    request = b'\xff\xff\xff\xffrcon "' + password.encode("ascii") + b'" sh1x_status'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.settimeout(0.4)
        sock.sendto(request, ("127.0.0.1", port))
        try:
            return sock.recvfrom(4096)[0].decode("ascii", errors="replace")
        except (socket.timeout, ConnectionResetError):
            return ""


def wait_until(predicate, seconds, label, processes=()):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for process in processes:
            if process.poll() is not None:
                raise AssertionError("%s exited early (code %s)" % (label, process.returncode))
        if predicate():
            return
        time.sleep(0.4)
    raise AssertionError("timed out waiting for " + label)


def write_client_ini(client_root):
    (client_root / "dwauth.ini").write_text(
        "127.0.0.1\n3074\n127.0.0.1\n3074\n3ea\n", encoding="ascii")
    (client_root / "stun.ini").write_text("127.0.0.1\n" * 10, encoding="ascii")


def main():
    try:
        from Crypto.Cipher import DES3  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("run this check with the lobby virtual environment (pycryptodome required)") from exc
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True,
                    help="Exact 1.1.1.13 asset installation, read only")
    ap.add_argument("--client-root", type=Path, required=True,
                    help="Isolated copy containing C1.exe and adjacent C1.dll")
    ap.add_argument("--lobby", type=Path, required=True,
                    help="Exact 1.1.1.13 Python lobby checkout, read only")
    ap.add_argument("--exe", type=Path, required=True,
                    help="Locally built native Windows match server")
    args = ap.parse_args()
    install = args.install.resolve()
    client_root = args.client_root.resolve()
    lobby_source = args.lobby.resolve()
    exe = args.exe.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not client_root.is_relative_to(temp_root) or not client_root.name.startswith("codol-11113-"):
        ap.error("client-root must be an isolated codol-11113-* copy under system temp")
    for required in (install / "main", install / "client_shipRetail",
                     client_root / "C1.exe", client_root / "C1.dll",
                     lobby_source / "dw-capture.py", exe):
        if not required.exists():
            ap.error("missing exact-build input: %s" % required)
    if sys.platform != "win32":
        ap.error("this check runs the Windows client and server")

    root = Path(__file__).resolve().parent.parent
    scripts = root / "bin" / "home" / "codol_rawfiles"
    scratch = Path(tempfile.mkdtemp(prefix="codol-11113-stack-"))
    state = scratch / "state"
    home = scratch / "home"
    state.mkdir()
    (home / "main").mkdir(parents=True)
    sys.path.insert(0, str(root / "tools"))
    import codol_package
    codol_package.build_pack(str(home / "main" / codol_package.PACK))
    copied_lobby = scratch / "lobby"
    shutil.copytree(lobby_source, copied_lobby,
                    ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.log"))
    (state / "securitykey.bin").write_bytes(secrets.token_bytes(16))
    password = secrets.token_hex(16)
    (state / "native_server_rcon.txt").write_text(password + "\n", encoding="ascii")
    port = unused_udp_port()
    write_client_ini(client_root)

    env = os.environ.copy()
    env.update(CODOL_STATE_DIR=str(state), CODOL_ADMISSION="0", CODOL_ADMISSION_PORT="0",
               CODOL_INSTANCES="0", CODOL_MM_HOST_PORT=str(port),
               CODOL_MATCH_RCON_HOST="127.0.0.1", CODOL_MATCH_RCON_PORT=str(port),
               CODOL_MATCH_CONTROL_DEDUP_SECONDS="0")
    # Use the base interpreter directly, with the current venv's crypto wheel.
    # The Windows venv redirector otherwise introduces an untracked child PID.
    env["PYTHONPATH"] = sysconfig.get_paths()["purelib"]
    crypto_probe = subprocess.run(
        [sys._base_executable, "-c", "from Crypto.Cipher import DES3"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )
    if crypto_probe.returncode != 0:
        raise RuntimeError("lobby interpreter cannot import pycryptodome")
    flags = subprocess.CREATE_NO_WINDOW
    processes = []
    handles = []
    try:
        lobby_out = (scratch / "lobby.stdout").open("wb")
        lobby_err = (scratch / "lobby.stderr").open("wb")
        handles.extend((lobby_out, lobby_err))
        lobby = subprocess.Popen([sys._base_executable, str(copied_lobby / "dw-capture.py"),
                                  "--host", "127.0.0.1", "--port", "3074", "--no-alt",
                                  "--log", str(state / "dw-capture.log"), "--respond"],
                                 cwd=copied_lobby, env=env, stdin=subprocess.DEVNULL,
                                 stdout=lobby_out, stderr=lobby_err, creationflags=flags)
        processes.append(lobby)

        def lobby_listening():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.25)
                return sock.connect_ex(("127.0.0.1", 3074)) == 0

        wait_until(lobby_listening, 15, "lobby TCP listener", processes)
        server_out = (scratch / "server.stdout").open("wb")
        server_err = (scratch / "server.stderr").open("wb")
        handles.extend((server_out, server_err))
        command = [str(exe),
                   "+set", "dedicated", "2", "+set", "fs_basepath", str(install),
                   "+set", "fs_homepath", str(home),
                   "+set", "codol_clientExe", str(client_root / "C1.exe"),
                   "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(port),
                   "+set", "rcon_password", password, "+set", "logfile", "2",
                   "+set", "codol_scriptPath", str(scripts),
                   "+set", "codol_scriptOverlay", str(scripts),
                   "+set", "codol_scriptNativeOverlay", str(scripts),
                   "+set", "codol_securityKeyPath", str(state / "securitykey.bin"),
                   "+set", "codol_admissionRequired", "0",
                   "+set", "codol_profilePath", str(copied_lobby / "resources"),
                   "+set", "codol_zoneType", "mp",
                   "+set", "codol_sessionMap", "mp_rust",
                   "+set", "g_gametype", "dm", "+map", "mp_rust"]
        command_chars = len(subprocess.list2cmdline(command[1:]))
        if command_chars >= 8192:
            raise AssertionError("native startup command exceeds the explicit 8192-byte limit")
        server = subprocess.Popen(command, cwd=exe.parent, env=env,
                                  stdin=subprocess.DEVNULL, stdout=server_out,
                                  stderr=server_err, creationflags=flags)
        processes.append(server)
        wait_until(lambda: "map=mp_rust" in status(port, password) and
                   "gametype=dm" in status(port, password),
                   90, "native mp_rust/dm", processes)

        # Exercise the copied lobby dispatcher against the actual native process.
        os.environ.update(CODOL_STATE_DIR=str(state), CODOL_MATCH_RCON_HOST="127.0.0.1",
                          CODOL_MATCH_RCON_PORT=str(port),
                          CODOL_MATCH_CONTROL_DEDUP_SECONDS="0")
        sys.path.insert(0, str(copied_lobby))
        from handoff import match_server_control
        note = match_server_control.dispatch({"map": "mp_rust", "session_map": "mp_rust",
                                              "gametype": "war", "type": "mp"})
        if "native match control ->" not in note:
            raise AssertionError("lobby did not dispatch the Ready map plan")
        wait_until(lambda: "map=mp_rust" in status(port, password) and
                   "gametype=war" in status(port, password),
                   90, "native Ready dispatch to mp_rust/war", processes)

        console = client_root / "main" / "console_mp.log"
        old_size = console.stat().st_size if console.exists() else 0
        client_out = (scratch / "client.stdout").open("wb")
        client_err = (scratch / "client.stderr").open("wb")
        handles.extend((client_out, client_err))
        client = subprocess.Popen([str(client_root / "C1.exe"), "+set", "dw_username",
                                   "CodexLocal", "+set", "969", "100", "+set",
                                   "com_maxfps", "0"],
                                  cwd=client_root, env=env, stdin=subprocess.DEVNULL,
                                  stdout=client_out, stderr=client_err, creationflags=flags)
        processes.append(client)

        def client_and_lobby_ready():
            if not console.exists() or console.stat().st_size <= old_size:
                return False
            with console.open("rb") as stream:
                stream.seek(old_size)
                fresh_client_log = stream.read().decode("utf-8", errors="replace")
            lobby_log = state / "dw-capture.log"
            if not lobby_log.exists():
                return False
            fresh_lobby_log = lobby_log.read_text(encoding="utf-8", errors="replace")
            return ("ui_viewer_mp" in fresh_client_log and
                    "AUTH REPLY TASK_REPLY" in fresh_lobby_log)

        wait_until(client_and_lobby_ready, 65, "real C1 authentication and UI zone", processes)
        print("PASS isolated lobby TCP, native mp_rust/dm, lobby Ready RCON to war, "
              "and real C1 authentication/UI zone")
        print("Native startup command: %d characters" % command_chars)
        print("Evidence directory: %s" % scratch)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=8)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
