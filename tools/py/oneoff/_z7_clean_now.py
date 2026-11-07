# -*- coding: utf-8 -*-
"""Kill only the processes this session started. Never touch pid 17624
(the pre-existing elevated agent)."""
import os
import subprocess

KEEP = {17624}
NAMES = ("codoMP_client_shipRetail", "AboProbe", "IIPSHostApp",
         "cmd", "python")


def ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True)
    return r.stdout.decode("utf-8", "replace")


rows = ps(
    "Get-CimInstance Win32_Process | "
    "Where-Object { $_.Name -match 'codoMP|AboProbe|IIPSHostApp' } | "
    "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.Name }")
print("--- game-tree processes ---")
print(rows.strip() or "(none)")

for line in rows.split():
    if "|" not in line:
        continue
    pid, name = line.split("|", 1)
    pid = int(pid)
    if pid in KEEP:
        print("  KEEP", pid, name)
        continue
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid],
                   capture_output=True)
    print("  killed", pid, name)

# my own helper scripts, identified by exact command line
mine = ps(
    "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
    "Where-Object { $_.CommandLine -match '_lobby_watch|agent_client|"
    "lobby_probe_server|lobby_socket_server|lobby_plain_probe' } | "
    "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
print("--- my python helpers ---")
for line in mine.strip().splitlines():
    if "|" not in line:
        continue
    pid, cmdline = line.split("|", 1)
    pid = int(pid)
    if pid in KEEP:
        print("  KEEP", pid, cmdline.strip()[:90])
        continue
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid],
                   capture_output=True)
    print("  killed", pid, cmdline.strip()[:90])
