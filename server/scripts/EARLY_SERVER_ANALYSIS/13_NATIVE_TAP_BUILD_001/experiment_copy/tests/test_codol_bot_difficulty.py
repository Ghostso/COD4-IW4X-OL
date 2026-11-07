"""Exercise all four authored bot tiers in isolated native MP matches."""

import argparse
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time

from test_codol_local_stack import unused_udp_port
from codol_live_guard import refuse_parallel_game


def rcon(port, password, command):
    packet = b"\xff" * 4 + b'rcon "' + password.encode("ascii") + b'" ' + command.encode("ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.8)
        sock.sendto(packet, ("127.0.0.1", port))
        try:
            return sock.recv(8192).decode("ascii", errors="replace")
        except (socket.timeout, ConnectionResetError):
            return ""


def run_tier(root, install, client, exe, tier):
    with tempfile.TemporaryDirectory(prefix=f"codol-bot-{tier}-") as temporary:
        scratch = Path(temporary)
        home = scratch / "home"
        (home / "main").mkdir(parents=True)
        sys.path.insert(0, str(root / "tools"))
        import codol_package
        codol_package.build_pack(str(home / "main" / codol_package.PACK))
        key = scratch / "securitykey.bin"
        key.write_bytes(secrets.token_bytes(16))
        password = secrets.token_hex(16)
        port = unused_udp_port()
        scripts = root / "bin" / "home" / "codol_rawfiles"
        log = home / "main" / "qconsole.log"
        command = [str(exe), "+set", "dedicated", "2", "+set", "fs_basepath", str(install),
                   "+set", "fs_homepath", str(home), "+set", "codol_clientExe", str(client / "C1.exe"),
                   "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(port),
                   "+set", "rcon_password", password, "+set", "logfile", "2", "+set", "logrcon", "1",
                   "+set", "developer", "1", "+set", "codol_scriptPath", str(scripts),
                   "+set", "codol_scriptOverlay", str(scripts), "+set", "codol_scriptNativeOverlay", str(scripts),
                   "+set", "codol_securityKeyPath", str(key), "+set", "codol_admissionRequired", "0",
                   "+set", "codol_profilePath", str(scratch / "profiles"), "+set", "codol_zoneType", "mp",
                   "+set", "codol_sessionMap", "mp_killhouse_sh", "+set", "g_gametype", "dm",
                   "+set", "scr_dm_scorelimit", "0", "+set", "scr_dm_timelimit", "0",
                   "+set", "scr_combat_scorelimit", "0", "+set", "scr_combat_timelimit", "0",
                   "+set", "scr_codol_bots", "9", "+set", "sv_botDifficulty", tier,
                   "+map", "mp_killhouse_sh"]
        with (scratch / "stdout").open("wb") as out, (scratch / "stderr").open("wb") as err:
            process = subprocess.Popen(command, cwd=exe.parent, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(f"{tier} server exited during startup ({process.returncode})")
                status = rcon(port, password, "sh1x_status")
                text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
                classes = [int(value) for value in re.findall(
                    rf"CoDOL bot difficulty: {tier} class (\d+) for Training \d+", text)]
                if "bots=9" in status and len(classes) >= 9 and "CoDOL bot difficulty: loaded recruit/regular/hardened/veteran" in text:
                    break
                time.sleep(0.5)
            else:
                relevant = [line for line in text.splitlines()
                            if "CoDOL bot difficulty" in line or "script runtime error" in line.lower()
                            or "classForDifficulty" in line or "spawnBots" in line]
                tail = " | ".join(relevant[-24:]).encode("ascii", "backslashreplace").decode("ascii")
                raise AssertionError(f"{tier} did not start nine bots from the mounted difficulty/class tables; "
                                     f"bots_present={'bots=9' in status} classes={classes!r} relevant_log={tail!r}")
            allowed = [0, 1, 2, 7] if tier == "recruit" else list(range(9))
            expected = [allowed[i % len(allowed)] for i in range(9)]
            assert classes[:9] == expected, f"{tier} classes {classes[:9]} expected {expected}"
            assert "script runtime error" not in text.lower(), f"{tier} script runtime error"
            print(f"PASS {tier}: classes {classes[:9]}; exact table loaded")
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--client-root", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    install, client, exe = (path.resolve() for path in (args.install, args.client_root, args.exe))
    for required in (install / "main", client / "C1.exe", exe):
        if not required.exists():
            ap.error(f"missing exact-build input: {required}")
    refuse_parallel_game()
    for tier in ("recruit", "regular", "hardened", "veteran"):
        run_tier(root, install, client, exe, tier)


if __name__ == "__main__":
    main()
