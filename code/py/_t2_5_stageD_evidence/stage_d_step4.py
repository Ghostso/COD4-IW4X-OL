"""T-2.5 Stage D step 4: working invocation form + the -qa TCLS gate, with module sampling.

Uses the shipped launcher form (one quoted app path, UseShellExecute=true) and appends
-qa inside the quoted-path argument list, then samples the client's loaded modules to see
whether the full Ayria chain (incl. CodolGameServer.Localnet32) appears. Nothing is terminated.
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
WANT = ("Bootstrapper32.dll", "Localnetworking.Ayria32", "Platformwrapper.Ayria32",
        "Alwaysoffline.LocalNet32", "CodolGameServer.Localnet32")


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


def modules_of(pid: int) -> list[str]:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "try { (Get-Process -Id " + str(pid) + " -ErrorAction Stop).Modules | "
         "Select-Object -ExpandProperty ModuleName } catch { }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def port_rows() -> list[dict]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=False).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() not in ("TCP", "UDP"):
            continue
        local = parts[1]
        if ":" in local and local.rsplit(":", 1)[1].isdigit() and int(local.rsplit(":", 1)[1]) in (28960, 28961, 28962, 28970):
            rows.append({"protocol": parts[0].upper(), "local": local, "ownerPid": parts[-1]})
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    before = {r["ProcessId"] for r in ps_rows()}
    doc: dict = {"scope": "shipped form + -qa; nothing terminated by this script", "startedAt": iso(time.time())}

    ps = ("$ErrorActionPreference='Stop'; "
          "$si=[System.Diagnostics.ProcessStartInfo]::new(); "
          "$si.FileName='" + str(INJECTOR) + "'; "
          "$si.Arguments=[char]34+'" + str(TARGET) + "'+[char]34+' -qa'; "
          "$si.WorkingDirectory='" + str(GAME) + "'; "
          "$si.UseShellExecute=$true; "
          "$p=[System.Diagnostics.Process]::Start($si); $p.WaitForExit(); "
          "Write-Output ('injector-exit=' + $p.ExitCode)")
    doc["argumentsForm"] = "<injector> \"<target>\" -qa  (UseShellExecute=true)"
    env = os.environ.copy()
    env.update({"OLMOD_PROCESS_ROLE": "combined", "OLMOD_DEDICATED_CONTROL_PORT": "28961",
                "OLMOD_CLIENT_BRIDGE_PORT": "28962", "OLMOD_ROOM_OWNER_PORT": "28970",
                "OLMOD_CONSOLE_LOG": "1", "OLMOD_CLAIM_LOBBY": "1", "OLMOD_CLIENT_INSTANCE": "1"})
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps], cwd=str(GAME),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, env=env, check=False)
    doc["outerProcess"] = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    pid = None
    samples = []
    deadline = time.time() + 45
    while time.time() < deadline:
        rows = ps_rows()
        clients = [r for r in rows if r["ProcessId"] not in before and
                   (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
        if clients and pid is None:
            pid = clients[0]["ProcessId"]
        sample = {"at": iso(time.time()), "clientPids": [r["ProcessId"] for r in clients],
                  "ports": [p["local"] for p in port_rows()]}
        if pid is not None and clients:
            mods = modules_of(pid)
            sample["moduleCount"] = len(mods)
            sample["wanted"] = {w: (w.casefold() in {m.casefold() for m in mods}) for w in WANT}
            sample["codolExports"] = [m for m in mods if "codol" in m.lower() or "ayria" in m.lower()
                                      or "localnet" in m.lower() or "always" in m.lower()]
        samples.append(sample)
        if pid is not None and not clients and len(samples) > 4:
            break
        time.sleep(2.0)
    doc["pid"] = pid
    doc["samples"] = samples
    doc["finalClients"] = [r for r in ps_rows() if (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
    for name in ("Bootstrapper32.log", "CODOLLauncher.log"):
        path = GAME / "Ayria/Logs" / name
        doc[name] = path.read_text(encoding="utf-8", errors="replace")[-4000:] if path.is_file() else None
    doc["endedAt"] = iso(time.time())
    (EVIDENCE / "stageD_step4.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("outer:", proc.returncode, proc.stdout.strip(), proc.stderr.strip()[:300])
    print("client pid:", pid)
    for s in samples:
        if s.get("wanted") is not None:
            print("  ", s["at"], "pid", s["clientPids"], "mods", s.get("moduleCount"),
                  json.dumps(s.get("codolExports"), ensure_ascii=False))
        else:
            print("  ", s["at"], "pid", s["clientPids"], "ports", s.get("ports"))
    print("final clients:", json.dumps(doc["finalClients"], ensure_ascii=False)[:300])
    print("Bootstrapper32.log:", json.dumps(doc["Bootstrapper32.log"], ensure_ascii=False)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
