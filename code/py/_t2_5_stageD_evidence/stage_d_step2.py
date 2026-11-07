"""T-2.5 Stage D step 2: decisive injector-invocation test.

CodolGame.py appends -qa, so Injector32 receives two tokens. Its own usage string is
  Missing commandline. Usage: Injector**.exe "app.exe"
This test runs the documented single-argument form and watches whether a client appears,
stays alive, and loads the Ayria module chain. Nothing is terminated by this script.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
GAME = Path("E:/CODOL_SANDBOX/RUN001")
INJECTOR = GAME / "Ayria/Injector32.exe"
TARGET = GAME / "codoMP_client_shipRetail.exe"
LOG = GAME / "Ayria/Logs/T25_launcher_direct.log"
TZ = timezone(timedelta(hours=8))
PORTS = (28960, 28961, 28962, 28970)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0800"


def ps_rows() -> list[dict]:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath | ConvertTo-Json -Depth 2 -Compress"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout
    try:
        rows = json.loads(out)
    except Exception:
        return []
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def codol(rows: list[dict]) -> list[dict]:
    return [r for r in rows if (r.get("Name") or "").lower() in
            ("codomp_client_shipretail.exe", "ol_room_owner.exe", "injector32.exe")
            or "CODOL_SANDBOX" in (r.get("ExecutablePath") or "").upper()]


def port_rows() -> list[dict]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=False).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() not in ("TCP", "UDP"):
            continue
        local = parts[1]
        if ":" in local and local.rsplit(":", 1)[1].isdigit() and int(local.rsplit(":", 1)[1]) in PORTS:
            rows.append({"protocol": parts[0].upper(), "local": local,
                         "state": parts[3] if parts[0].upper() == "TCP" else "UDP", "ownerPid": parts[-1]})
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    doc: dict = {"scope": "single-argument injector form; nothing terminated by this script"}
    before = {r["ProcessId"] for r in ps_rows()}
    doc["pre"] = {"codol": codol(ps_rows()), "ports": port_rows(), "at": iso(time.time())}

    env = os.environ.copy()
    env.update({"OLMOD_PROCESS_ROLE": "combined", "OLMOD_DEDICATED_CONTROL_PORT": "28961",
                "OLMOD_CLIENT_BRIDGE_PORT": "28962", "OLMOD_ROOM_OWNER_PORT": "28970",
                "OLMOD_CONSOLE_LOG": "1", "OLMOD_CLAIM_LOBBY": "1", "OLMOD_CLIENT_INSTANCE": "1"})
    argv = [str(INJECTOR), str(TARGET)]
    doc["argv"] = argv
    started = time.time()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("w", encoding="utf-8", errors="replace") as log:
        done = subprocess.run(argv, cwd=str(GAME), stdin=subprocess.DEVNULL,
                              stdout=log, stderr=subprocess.STDOUT, timeout=30,
                              creationflags=subprocess.CREATE_NO_WINDOW, env=env, check=False)
    doc["injector"] = {"returncode": done.returncode, "startedAt": iso(started), "endedAt": iso(time.time())}

    timeline = []
    pid = None
    deadline = time.time() + 25
    while time.time() < deadline:
        rows = ps_rows()
        new = [r for r in rows if r["ProcessId"] not in before and
               (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
        alive = [r for r in rows if r["ProcessId"] not in before and
                 (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
        if new and pid is None:
            pid = new[0]["ProcessId"]
        timeline.append({"at": iso(time.time()), "newClientPids": [r["ProcessId"] for r in new],
                         "clientAlive": bool(alive), "ports": [p["local"] for p in port_rows()]})
        if pid is not None and not alive and len(timeline) > 4:
            break
        time.sleep(0.5)
    doc["pid"] = pid
    doc["timeline"] = timeline
    doc["post"] = {"codol": codol(ps_rows()), "ports": port_rows(), "at": iso(time.time())}
    if LOG.is_file():
        doc["injectorLog"] = LOG.read_text(encoding="utf-8", errors="replace")[:4000]
    boot = GAME / "Ayria/Logs/Bootstrapper32.log"
    doc["bootstrapperLog"] = None
    if boot.is_file():
        t = boot.read_text(encoding="utf-8", errors="replace")
        doc["bootstrapperLog"] = {"size": boot.stat().st_size, "tail": t[-4000:]}
    (EVIDENCE / "stageD_step2.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("injector exit:", done.returncode)
    print("argv:", json.dumps(argv, ensure_ascii=False))
    print("first client pid:", pid)
    print("client appearance timeline (first/last):")
    if timeline:
        print("  ", json.dumps(timeline[0], ensure_ascii=False))
        print("  ", json.dumps(timeline[len(timeline) // 2], ensure_ascii=False))
        print("  ", json.dumps(timeline[-1], ensure_ascii=False))
    print("post codol:", json.dumps(doc["post"]["codol"], ensure_ascii=False)[:500])
    print("post ports:", json.dumps(doc["post"]["ports"], ensure_ascii=False))
    print("injector log:", json.dumps(doc.get("injectorLog"), ensure_ascii=False)[:600])
    print("bootstrapper log:", json.dumps(doc["bootstrapperLog"], ensure_ascii=False)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
