# -*- coding: utf-8 -*-
import subprocess
for pid in [26968,27892,75172,81568]:
    r=subprocess.run(["powershell","-NoProfile","-Command",
      "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % pid],
      capture_output=True)
    print(pid, ":", r.stdout.decode("utf-8","replace").strip()[:200])
