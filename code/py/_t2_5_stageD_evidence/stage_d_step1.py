"""T-2.5 Stage D step 1: pre-launch snapshot, single-client launch, post-launch snapshot.

Approved scope: ONE sandbox client, no termination, no setEnabled, no port-release probe.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
RUNTIME = Path("F:/桌面/ol/ol-mod-olfinal/tools/runtime")
GAME = Path("E:/CODOL_SANDBOX/RUN001")
PY = sys.executable
TZ = timezone(timedelta(hours=8))
PORTS = (28960, 28961, 28962, 28970)
TARGET = "codoMP_client_shipRetail.exe"


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def ps_table() -> list[dict]:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout
    try:
        rows = json.loads(out)
    except Exception:
        return []
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def codol_rows(rows: list[dict]) -> list[dict]:
    hits = []
    for r in rows:
        name = (r.get("Name") or "").lower()
        path = (r.get("ExecutablePath") or "")
        if (name in (TARGET.lower(), "ol_room_owner.exe", "injector32.exe")
                or "CODOL_SANDBOX" in path.upper()):
            hits.append(r)
    return hits


def port_rows() -> list[dict]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=False).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() not in ("TCP", "UDP"):
            continue
        local = parts[1]
        if ":" not in local:
            continue
        tail = local.rsplit(":", 1)[1]
        if tail.isdigit() and int(tail) in PORTS:
            rows.append({"protocol": parts[0].upper(), "local": local,
                         "state": parts[3] if parts[0].upper() == "TCP" else "UDP",
                         "ownerPid": parts[-1]})
    return rows


def snapshot(label: str) -> dict:
    rows = ps_table()
    live = codol_rows(rows)
    snap = {"label": label, "at": iso(datetime.now(TZ).timestamp()),
            "totalProcesses": len(rows), "codolProcesses": live, "ports": port_rows()}
    (EVIDENCE / ("snapshot_" + label + ".json")).write_text(
        json.dumps({"snapshot": snap, "allProcesses": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return snap


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    doc: dict = {"scope": "one sandbox client; no termination; no setEnabled; no port release probe"}
    doc["pre"] = snapshot("pre")
    print("PRE codol processes:", json.dumps(doc["pre"]["codolProcesses"], ensure_ascii=False)[:600])
    print("PRE ports:", json.dumps(doc["pre"]["ports"], ensure_ascii=False))

    argv = [PY, str(RUNTIME / "CodolGame.py"), "launch", "--game-dir", str(GAME), "--wait", "20"]
    started = datetime.now(TZ)
    proc = subprocess.run(argv, cwd=str(RUNTIME), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False, timeout=180)
    ended = datetime.now(TZ)
    doc["launch"] = {"argv": argv, "cwd": str(RUNTIME), "startedAt": iso(started.timestamp()),
                     "endedAt": iso(ended.timestamp()), "returncode": proc.returncode,
                     "stdout": proc.stdout, "stderr": proc.stderr}
    (EVIDENCE / "stageD_launch.log").write_text(
        "ARGV: " + json.dumps(argv, ensure_ascii=False) + "\nCWD: " + str(RUNTIME) +
        "\nSTART: " + doc["launch"]["startedAt"] + "\nEND: " + doc["launch"]["endedAt"] +
        "\nEXIT: " + str(proc.returncode) + "\n--- STDOUT ---\n" + proc.stdout +
        "\n--- STDERR ---\n" + proc.stderr + "\n", encoding="utf-8")
    print("LAUNCH exit:", proc.returncode)
    print("LAUNCH stdout:", proc.stdout.strip()[:800])
    print("LAUNCH stderr:", proc.stderr.strip()[:800])

    doc["post"] = snapshot("post")
    print("POST codol processes:", json.dumps(doc["post"]["codolProcesses"], ensure_ascii=False)[:900])
    print("POST ports:", json.dumps(doc["post"]["ports"], ensure_ascii=False))

    ps_path = GAME / "Ayria" / "ol-mod-process-state.json"
    for cand in sorted((GAME / "Ayria").glob("*process*")):
        if cand.is_file():
            ps_path = cand
            break
    doc["processState"] = {"path": str(ps_path), "exists": ps_path.is_file()}
    if ps_path.is_file():
        doc["processState"]["content"] = ps_path.read_text(encoding="utf-8", errors="replace")[:2000]
    doc["launcherLog"] = None
    log = GAME / "Ayria" / "Logs" / "CODOLLauncher.log"
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")
        doc["launcherLog"] = {"path": str(log), "size": log.stat().st_size, "tail": text[-3000:]}
    (EVIDENCE / "stageD_step1.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
