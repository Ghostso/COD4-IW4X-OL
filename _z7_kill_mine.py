# -*- coding: utf-8 -*-
"""Stop only the two lobby servers this session started, by pid."""
import subprocess

PIDS = [24624, 51004, 33936, 1832, 19204, 22556]

for pid in PIDS:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue; 'done'" % pid],
        capture_output=True)
    print("stop %-6d %s" % (pid, r.stdout.decode("utf-8", "replace").strip()))
