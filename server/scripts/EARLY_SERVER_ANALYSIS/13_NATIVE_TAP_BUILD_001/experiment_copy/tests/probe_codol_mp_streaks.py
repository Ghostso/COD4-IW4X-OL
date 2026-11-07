"""Isolated native MP probe for RC-XD death/reuse and offhand recovery.

Runs bot clients through the real server script and weapon paths. It cannot
prove the human C1 input or HUD path. The live UDP/17733 server is untouched.
"""

import argparse
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

from test_codol_local_stack import unused_udp_port
from codol_live_guard import refuse_parallel_game


def rcon(port, password, command):
    message = b"\xff\xff\xff\xffrcon \"" + password.encode("ascii") + b"\" " + command.encode("ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.8)
        sock.sendto(message, ("127.0.0.1", port))
        try:
            return sock.recv(8192).decode("ascii", errors="replace")
        except (socket.timeout, ConnectionResetError):
            return ""


def wait_for(log, marker, since, process, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"server exited {process.returncode} waiting for {marker}")
        if log.exists():
            text = log.read_text(encoding="utf-8", errors="replace")
            index = text.find(marker, since)
            if index >= 0:
                return text[index:].splitlines()[0], len(text)
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {marker}; log: {log}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--client-root", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    install, client, exe = (p.resolve() for p in (args.install, args.client_root, args.exe))
    if not (install / "main").exists() or not (client / "C1.exe").exists() or not exe.exists():
        ap.error("exact install, C1.exe, or server executable missing")
    refuse_parallel_game()
    scratch = Path(tempfile.mkdtemp(prefix="codol-mp-streak-probe-"))
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
               "+set", "scr_codol_bots", "2", "+set", "scr_dm_scorelimit", "0",
               "+set", "scr_dm_timelimit", "0", "+set", "scr_combat_scorelimit", "0",
               "+set", "scr_combat_timelimit", "0", "+map", "mp_killhouse_sh"]
    out = (scratch / "server.stdout").open("wb")
    err = (scratch / "server.stderr").open("wb")
    process = subprocess.Popen(command, cwd=exe.parent, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"server exited during startup: {process.returncode}")
            if "bots=2" in rcon(port, password, "sh1x_status"):
                break
            time.sleep(0.5)
        else:
            raise AssertionError("two native bots never became ready")
        offset = len(log.read_text(encoding="utf-8", errors="replace"))

        def issue(request, marker):
            nonlocal offset
            rcon(port, password, f'set scr_codol_usekillstreak "{request}"')
            line, offset = wait_for(log, marker, offset, process)
            print(line)
            return line

        def state():
            nonlocal offset
            start = offset
            line = issue("state 0", "CoDOL killstreak test: state Training 1")
            offhands, offset = wait_for(log, "CoDOL killstreak test: offhands Training 1", start, process)
            print(offhands)
            return line, offhands

        # The test client uses the same script dispatcher and native inventory
        # as a human, then dies while remote control is active.
        issue("rcsafe 1", "CoDOL killstreak test: rcsafe 1")
        _, offhands = state()
        assert "hold 0 " in offhands, offhands
        issue("give 0 rcbomb_mp", "owned [rcbomb_mp#")
        issue("activate 0 rcbomb_mp", "activated rcbomb_mp")
        time.sleep(2)
        line, offhands = state()
        assert "remoteCtl 1" in line and "hold 1 " in offhands, (line, offhands)
        issue("suicide 0", "suicide Training 1")
        # The T5-style car continues after its driver dies. The RC timer is 30s.
        time.sleep(33)
        line, offhands = state()
        assert "alive 1" in line and "remoteCtl 0" in line and "rcRule 0/" in line, line
        assert "hold 0 " in offhands, offhands
        # The respawn can face a wall where RC placement is correctly refused.
        # Use a known player spawn, then prove PMove has grounded the bot.
        issue("relocate 0 4246 -732 4 180", "relocated Training 1")
        for _ in range(10):
            time.sleep(0.5)
            line, _ = state()
            if "onGround 1" in line:
                break
        else:
            raise AssertionError("relocated bot never reached ground before second RC-XD use")
        issue("give 0 rcbomb_mp", "owned [rcbomb_mp#")
        # Keep the bot grounded while the weapon-change use thread starts.
        # Otherwise a jumping bot can refuse the RC placement before the
        # second-use state machine is reached.
        issue("activate 0 rcbomb_mp hold", "activated rcbomb_mp")
        time.sleep(2)
        line, offhands = state()
        assert "remoteCtl 1" in line and "hold 1 " in offhands, (line, offhands)
        rcon(port, password, 'set scr_codol_usekillstreak "freeze 0 0"')
        issue("rcsafe 0", "CoDOL killstreak test: rcsafe 0")
        for _ in range(30):
            time.sleep(1)
            line, offhands = state()
            if "remoteCtl 0" in line and "rcRule 0/" in line and "hold 0 " in offhands:
                break
        else:
            raise AssertionError("second RC-XD ride never released remote/offhand state")
        for slot, weapon in ((0, "frag_grenade_mp"), (1, "concussion_grenade_mp")):
            rcon(port, password, f'set scr_codol_equiptest "0 {slot} {weapon}"')
            line, offset = wait_for(log, f"CoDOL equiptest: grenade_fire {weapon} by Training 1", offset, process, 18)
            print(line)
        recent = log.read_text(encoding="utf-8", errors="replace")
        assert "script runtime error" not in recent.lower(), "script runtime error in probe log"
        print(f"PASS native RC-XD death/reuse and lethal/tactical throws; evidence: {log}")
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=8)
        out.close()
        err.close()


if __name__ == "__main__":
    main()
