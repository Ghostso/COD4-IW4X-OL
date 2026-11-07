"""Isolated exact-build Windows server boot and loopback control smoke test.

Run with a 1.1.1.13 asset install, C1.exe, and the matching lobby checkout.
The test owns only a temporary home/key and the process it starts.
"""

import argparse
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time

from codol_live_guard import refuse_parallel_game


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--exe", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    scripts = root / "bin" / "home" / "codol_rawfiles"
    for path in (args.install, args.client, args.reference, args.exe, scripts):
        if not path.exists():
            parser.error("required path is missing: %s" % path)
    refuse_parallel_game()
    port = free_udp_port()
    with tempfile.TemporaryDirectory(prefix="codol-11113-windows-boot-") as temporary:
        home = Path(temporary)
        (home / "main").mkdir()
        key = home / "securitykey.bin"
        key.write_bytes(secrets.token_bytes(16))
        password = secrets.token_hex(16)
        command = [str(args.exe),
                   "+set", "dedicated", "2",
                   "+set", "fs_basepath", str(args.install),
                   "+set", "fs_homepath", str(home),
                   "+set", "codol_clientExe", str(args.client),
                   "+set", "net_ip", "127.0.0.1",
                   "+set", "net_port", str(port),
                   "+set", "rcon_password", password,
                   "+set", "logfile", "2",
                   "+set", "codol_scriptPath", str(scripts),
                   "+set", "codol_scriptOverlay", str(scripts),
                   "+set", "codol_scriptNativeOverlay", str(scripts),
                   "+set", "codol_securityKeyPath", str(key),
                   "+set", "codol_admissionRequired", "0",
                   "+set", "codol_profilePath", str(args.reference / "resources"),
                   "+set", "codol_zoneType", "mp",
                   "+set", "codol_sessionMap", "mp_rust",
                   "+set", "g_gametype", "dm",
                   "+map", "mp_rust"]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(command, cwd=args.exe.parent,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   creationflags=flags)
        try:
            deadline = time.monotonic() + 90
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
                receiver.bind(("127.0.0.1", 0))
                receiver.settimeout(0.5)
                status = (b"\xff" * 4 + b'rcon "' + password.encode("ascii") +
                          b'" sh1x_status')
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise AssertionError("server exited before map startup (code %s)" % process.returncode)
                    receiver.sendto(status, ("127.0.0.1", port))
                    try:
                        reply = receiver.recvfrom(4096)[0]
                    except socket.timeout:
                        continue
                    except ConnectionResetError:
                        # Windows reports ICMP port-unreachable while the process boots.
                        continue
                    if b"sh1x_status map=mp_rust" in reply:
                        break
                else:
                    raise AssertionError("server did not report mp_rust through loopback RCON")
            print("PASS Windows native server booted mp_rust/dm and answered loopback RCON")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
