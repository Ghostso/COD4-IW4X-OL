"""T-2.5 Stage D step 3: replicate the shipped Launch_OLMod.bat invocation exactly.

That launcher passes the target as ONE QUOTED argument with UseShellExecute=true.
Nothing is terminated by this script.
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
TZ = timezone(timedelta(hours=8))


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
    return [rows] if isinstance(rows, dict) else rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    before = {r["ProcessId"] for r in ps_rows()}
    doc: dict = {"scope": "shipped-launcher invocation form; nothing terminated by this script",
                 "startedAt": iso(time.time())}

    ps = ("$ErrorActionPreference='Stop'; "
          "$si=[System.Diagnostics.ProcessStartInfo]::new(); "
          "$si.FileName='" + str(INJECTOR) + "'; "
          "$si.Arguments=[char]34+'" + str(TARGET) + "'+[char]34; "
          "$si.WorkingDirectory='" + str(GAME) + "'; "
          "$si.UseShellExecute=$true; "
          "$p=[System.Diagnostics.Process]::Start($si); $p.WaitForExit(); "
          "Write-Output ('injector-exit=' + $p.ExitCode)")
    doc["powershell"] = ps
    env = os.environ.copy()
    env.update({"OLMOD_PROCESS_ROLE": "combined", "OLMOD_DEDICATED_CONTROL_PORT": "28961",
                "OLMOD_CLIENT_BRIDGE_PORT": "28962", "OLMOD_ROOM_OWNER_PORT": "28970",
                "OLMOD_CONSOLE_LOG": "1", "OLMOD_CLAIM_LOBBY": "1", "OLMOD_CLIENT_INSTANCE": "1"})
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps], cwd=str(GAME),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, env=env, check=False)
    doc["outerProcess"] = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    timeline = []
    pid = None
    deadline = time.time() + 25
    while time.time() < deadline:
        rows = ps_rows()
        clients = [r for r in rows if r["ProcessId"] not in before and
                   (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
        if clients and pid is None:
            pid = clients[0]["ProcessId"]
        timeline.append({"at": iso(time.time()), "clients": [r["ProcessId"] for r in clients]})
        if pid is not None and not clients and len(timeline) > 4:
            break
        time.sleep(0.5)
    doc["pid"] = pid
    doc["timeline"] = timeline
    doc["finalClients"] = [r for r in ps_rows() if (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
    launcher = GAME / "Ayria/Logs/CODOLLauncher.log"
    doc["launcherLog"] = launcher.read_text(encoding="utf-8", errors="replace")[:2000] if launcher.is_file() else None
    boot = GAME / "Ayria/Logs/Bootstrapper32.log"
    doc["bootstrapperLog"] = (boot.read_text(encoding="utf-8", errors="replace")[-3000:]
                              if boot.is_file() else None)
    doc["endedAt"] = iso(time.time())
    (EVIDENCE / "stageD_step3.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("outer:", proc.returncode, proc.stdout.strip(), proc.stderr.strip()[:300])
    print("client pid:", pid)
    for row in (timeline[0], timeline[len(timeline) // 2], timeline[-1]) if timeline else []:
        print("  ", json.dumps(row, ensure_ascii=False))
    print("final clients:", json.dumps(doc["finalClients"], ensure_ascii=False)[:400])
    print("launcherLog:", json.dumps(doc["launcherLog"], ensure_ascii=False)[:400])
    print("bootstrapperLog:", json.dumps(doc["bootstrapperLog"], ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
