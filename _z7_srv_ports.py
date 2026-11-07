# -*- coding: utf-8 -*-
import re, io, os
for f in ["lobby_server/lobby_socket_server.py",
          "lobby_server/lobby_plain_probe.py",
          "lobby_server/_auth_resp_test.py"]:
    p = os.path.join("CODOLServer", f)
    if not os.path.isfile(p):
        print("MISSING", p); continue
    print("="*70); print(p, os.path.getsize(p))
    with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    for m in re.finditer(r'\b(?:3074|8443|8446|443|127\.0\.0\.[12]|PORT|BIND|listen)\b[^\n]{0,80}', src):
        print("  ", m.group(0)[:110])
