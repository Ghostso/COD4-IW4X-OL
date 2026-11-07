"""Pre-run cleanup: kill game + stray python (KEEP the elevated agent), wait for
ports 8443/8446 to be free.  Pure-Python (no PowerShell) so it cannot be
broken by shell quoting."""
import re
import socket
import subprocess
import sys
import time
import os

KEEP_MARKERS = ("agent_client", "run_elevated_agent", "agent_server", "_agent",
                "z7_cleanup",
                # The auth / lobby services are persistent prerequisites.
                # Earlier this sweep killed fake_auth_tls.py every round,
                # which made the game exit with 0xFFFFFFFF at ~10 s.
                "fake_auth_tls", "lobby_plain_probe", "lsg_server",
                "lobby_probe_server", "lobby_socket_server")
GAME_NAMES = {
    "codlauncher", "callofdutyonline", "codol", "iw5mp", "iw5sp",
    "blackopsmp", "cod",
}
AGENT_PORT = 50508


def run(cmd):
    """Run a console tool.  Output is decoded leniently: tasklist/wmic emit
    GBK-encoded (CP936) text on this host, not UTF-8."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=90)
    except Exception as e:
        return "ERR %s" % e
    out = r.stdout or b""
    for enc in ("utf-8", "gbk", "cp936", "latin-1"):
        try:
            return out.decode(enc)
        except UnicodeDecodeError:
            continue
    return out.decode("latin-1", "replace")


def tasklist():
    out = run(["tasklist", "/FO", "CSV", "/NH"])
    rows = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[1].isdigit():
            rows.append((parts[0], int(parts[1])))
    return rows


def cmdline(pid):
    out = run(["wmic", "process", "where", "ProcessId=%d" % pid,
               "get", "CommandLine", "/format:list"])
    for line in out.splitlines():
        if line.startswith("CommandLine="):
            return line[len("CommandLine="):]
    return ""


def is_agent(pid):
    """True if `pid` is the elevated debug agent.

    The command-line test alone is NOT sufficient: `wmic ... get CommandLine`
    returns an EMPTY string for the elevated agent under this host's policy
    (verified 2026-10-02), which made the sweep try to kill it.  A taskkill
    against an elevated process silently fails without /F elevation, so the
    agent survived by luck.  Bind the authoritative check to the agent's
    listening port instead."""
    if pid == agent_listener_pid():
        return True
    cl = cmdline(pid).lower()
    return any(m in cl for m in KEEP_MARKERS)


_AGENT_PID = [None]


def agent_listener_pid():
    if _AGENT_PID[0] is not None:
        return _AGENT_PID[0]
    pid = None
    out = run(["netstat", "-ano", "-p", "tcp"])
    for line in out.splitlines():
        if "LISTENING" in line and (":%d " % AGENT_PORT) in line:
            pid = int(line.split()[-1])
            break
    _AGENT_PID[0] = pid
    return pid


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main():
    wait = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
    killed_game = killed_py = 0
    # 2026-10-02: the sweep used to kill ITSELF.  This script is a python.exe
    # whose command line is "python ..._z7_cleanup.py" -- it matches the
    # "non-agent python" rule, so the loop ran `taskkill /F /T` on its own PID
    # and the process died with rc=1 before printing anything.  That is why
    # every earlier invocation produced zero output.  Never target self, and
    # never target an ancestor.
    self_pid = os.getpid()
    parent_pid = os.getppid()
    agent_pid = agent_listener_pid()
    print("agent listener pid=%s (port %d)" % (agent_pid, AGENT_PORT))
    for name, pid in tasklist():
        low = name.lower()
        if low.endswith(".exe"):
            low = low[:-4]
        if pid in (self_pid, parent_pid):
            print("SELF  pid=%-7d %s  -> skip" % (pid, name))
            continue
        if pid == agent_pid:
            print("AGENT pid=%-7d %s  -> KEEP (port %d)" % (pid, name, AGENT_PORT))
            continue
        if low in GAME_NAMES:
            print("GAME  pid=%-7d %s  -> kill" % (pid, name))
            run(["taskkill", "/PID", str(pid), "/F", "/T"])
            killed_game += 1
        elif low == "python":
            if is_agent(pid):
                print("AGENT pid=%-7d KEEP" % pid)
            else:
                cl = cmdline(pid)
                print("PY    pid=%-7d kill  %s" % (pid, cl[:110]))
                run(["taskkill", "/PID", str(pid), "/F", "/T"])
                killed_py += 1
    print("killed: game=%d python=%d" % (killed_game, killed_py))

    print("waiting %.1fs for TIME_WAIT to clear..." % wait)
    time.sleep(wait)
    for p in (8443, 8446):
        print("port %d free=%s" % (p, port_free(p)))
    print("DONE")


if __name__ == "__main__":
    main()
