# -*- coding: utf-8 -*-
import os
items = [
 "run_lobby_elevated.bat",
 r"CODOLServer\lobby_server\mklobby_response.py",
 r"CODOLServer\_mainline\elevated_agent.py",
 r"CODOLServer\_mainline\agent_client.py",
 r"CODOLServer\lobby_server\lobby_probe_server.py",
 r"CODOLServer\lobby_server\lobby_socket_server.py",
 r"CODOLServer\_mainline\_lobby_watch.py",
 r"run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe",
]
for i in items:
    print("  %-62s %s" % (i, "OK  %d" % os.path.getsize(i) if os.path.isfile(i) else "*** MISSING ***"))
print()
print("=== portproxy currently ===")
import subprocess
r=subprocess.run(["netsh","interface","portproxy","show","v4tov4"],capture_output=True)
print(r.stdout.decode("gbk","replace"))
