"""Bypass the portproxy indirection WITHOUT touching any network config.

Hypothesis: netsh interface portproxy is a user-mode TCP forwarder and is the
only piece between our TLS server and the client.  The client's BD object
stays at BD_PENDING(3) and never reaches BD_INITIALIZING(2), i.e. it never
observes a complete reply -- exactly the symptom a broken/duplicating
forwarder would produce.

Instead of deleting the existing portproxy rules (a system network change),
this binds the probe to 127.0.0.3:443 -- a fresh loopback address inside
127.0.0.0/8 that no portproxy rule covers -- and points dwauth.ini at it.
Port 443 needs admin, so run this THROUGH the elevated agent.
ASCII only.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
LOBBY = os.path.join(ROOT, "CODOLServer", "lobby_server")
LOGS = os.path.join(ROOT, "CODOLServer", "logs")
GAMEDIR = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")
HOST = "127.0.0.3"
PORT = 443


def run(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=== whoami / admin check ===")
    print(run(["whoami"])[1])

    print("=== portproxy left untouched (see below) ===")
    rc, out, _ = run(["netsh", "interface", "portproxy", "show", "all"])
    print(out or "(empty)")

    print("=== bind probe directly on %s:%d ===" % (HOST, PORT))
    log = open(os.path.join(LOGS, "probe443.out"), "w")
    err = open(os.path.join(LOGS, "probe443.err"), "w")
    p = subprocess.Popen(
        [sys.executable, "-X", "utf8",
         os.path.join(LOBBY, "lobby_probe_server.py"),
         "--cert-dir", LOBBY, "--bind", HOST, "--port", str(PORT),
         "--log", os.path.join(LOGS, "lobby_probe443.jsonl")],
        cwd=ROOT, stdout=log, stderr=err)
    print("  probe pid=%d" % p.pid)
    time.sleep(2.5)

    rc, out, _ = run(["netstat", "-ano"])
    print("=== listeners on :443 ===")
    for line in out.splitlines():
        if ":443" in line and "LISTENING" in line:
            print("  " + line.strip())

    # Point dwauth.ini at the direct address: field3 = host, field4 = port.
    path = os.path.join(GAMEDIR, "dwauth.ini")
    backup = path + ".bak_direct443"
    if os.path.exists(path) and not os.path.exists(backup):
        open(backup, "w", encoding="ascii").write(
            open(path, encoding="ascii").read())
    open(path, "w", encoding="ascii", newline="\n").write(
        "127.0.0.1\n0\n%s\n%d\n0\n0\n0\n" % (HOST, PORT))
    print("=== dwauth.ini now ===")
    print(open(path, encoding="ascii").read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
