#!/usr/bin/env python3
"""138 动态卷: 通过项目自带的 elevated agent 运行一条命令（只读观测用）。

用法: python -X utf8 tools\dyn138_agent_run.py <argv...>
例:   python -X utf8 tools\dyn138_agent_run.py python -I run_codol_001\mem_dump_attach.py D:\...\runs\R4_dump --max-mb 700
"""
import json
import socket
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CFG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\elevated_agent.json"
CWD = r"D:\BaiduNetdiskDownload\使命召唤OL"

a = json.load(open(CFG, encoding="utf-8"))
print("[agent] pid=%s port=%s debug_privilege=%s" % (a.get("pid"), a.get("port"),
                                                     a.get("debug_privilege")))
argv = sys.argv[1:]
if not argv:
    print("usage: dyn138_agent_run.py <argv...>")
    raise SystemExit(2)
req = json.dumps({"token": str(a["token"]), "action": "run", "argv": argv,
                  "cwd": CWD, "timeout": 900}).encode("utf-8") + b"\n"
buf = b""
with socket.create_connection(("127.0.0.1", int(a["port"])), timeout=900) as s:
    s.sendall(req)
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        buf += c
r = json.loads(buf.decode("utf-8"))
print("[agent] ok=%s rc=%s" % (r.get("ok"), r.get("rc")))
if r.get("stdout"):
    print(r["stdout"])
if r.get("stderr"):
    sys.stderr.write(r["stderr"])
