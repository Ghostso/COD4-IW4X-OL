# -*- coding: utf-8 -*-
import subprocess
# stop the 4 python servers I started (33936,1832,19204,22556)
ids = [33936,1832,19204,22556]
for pid in ids:
    r = subprocess.run(["powershell","-NoProfile","-Command",
        "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue; 'ok'" % pid],
        capture_output=True, text=True)
    print("stop", pid, r.stdout.strip(), r.stderr.strip()[:100])
