"""T-2.5 Stage D: single combined experiment.

launch (shipped launcher form) -> confirm one live client -> ONE Frida attach ->
phase 1 read-only export probe (reloaded until the plugin module is visible) ->
phase 2 unmodified generated control script -> detach. The client is never terminated.

CodolGame.py's own launch form fails at the injector (ERROR_FILE_NOT_FOUND) before any
client exists; that is recorded as a Stage D finding. The launch form used here is the one
shipped in E:\CODOL_SANDBOX\RUN001\Launch_OLMod.bat.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
RUNTIME = Path("F:/桌面/ol/ol-mod-olfinal/tools/runtime")
CONTROL_SOURCE = Path("D:/BaiduNetdiskDownload/使命召唤OL/_t2_5_evidence_run2/generated_control_script.js")
PROBE_SOURCE = EVIDENCE / "t25_export_probe.js"
GAME = Path("E:/CODOL_SANDBOX/RUN001")
INJECTOR = GAME / "Ayria/Injector32.exe"
TARGET = GAME / "codoMP_client_shipRetail.exe"
TZ = timezone(timedelta(hours=8))
PORTS = (28960, 28961, 28962, 28970)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0800"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def powershell(script: str, timeout: int = 60) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False,
                          timeout=timeout).stdout


def ps_rows() -> list[dict]:
    out = powershell("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath | "
                     "ConvertTo-Json -Depth 2 -Compress", timeout=90)
    try:
        rows = json.loads(out)
    except Exception:
        return []
    return [rows] if isinstance(rows, dict) else rows


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
            rows.append({"protocol": parts[0].upper(), "local": local, "state": parts[3], "ownerPid": parts[-1]})
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    doc: dict = {"scope": "one client, one Frida attach, probe + production control script, no termination",
                 "startedAt": iso(time.time())}
    boot = GAME / "Ayria/Logs/Bootstrapper32.log"
    boot_offset = boot.stat().st_size if boot.is_file() else 0
    doc["bootstrapperLogSizeBefore"] = boot_offset

    before = {r["ProcessId"] for r in ps_rows()}
    doc["pre"] = {"codol": [r for r in ps_rows() if "CODOL_SANDBOX" in (r.get("ExecutablePath") or "").upper()],
                  "ports": port_rows(), "at": iso(time.time())}
    print("PRE ports:", doc["pre"]["ports"])

    # ---- launch via the shipped launcher form -------------------------------
    ps = ("$ErrorActionPreference='Stop'; "
          "$si=[System.Diagnostics.ProcessStartInfo]::new(); "
          "$si.FileName='" + str(INJECTOR) + "'; "
          "$si.Arguments=[char]34+'" + str(TARGET) + "'+[char]34+' -qa'; "
          "$si.WorkingDirectory='" + str(GAME) + "'; "
          "$si.UseShellExecute=$true; "
          "$p=[System.Diagnostics.Process]::Start($si); $p.WaitForExit(); "
          "Write-Output ('injector-exit=' + $p.ExitCode)")
    env = os.environ.copy()
    env.update({"OLMOD_PROCESS_ROLE": "combined", "OLMOD_DEDICATED_CONTROL_PORT": "28961",
                "OLMOD_CLIENT_BRIDGE_PORT": "28962", "OLMOD_ROOM_OWNER_PORT": "28970",
                "OLMOD_CONSOLE_LOG": "1", "OLMOD_CLAIM_LOBBY": "1", "OLMOD_CLIENT_INSTANCE": "1"})
    launched = subprocess.run(["powershell", "-NoProfile", "-Command", ps], cwd=str(GAME),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=120, env=env, check=False)
    doc["launch"] = {"form": '<Injector32.exe> "<target>" -qa with UseShellExecute=true',
                     "powershellReturncode": launched.returncode,
                     "stdout": launched.stdout, "stderr": launched.stderr, "at": iso(time.time())}
    print("launch:", launched.returncode, launched.stdout.strip(), launched.stderr.strip()[:200])

    pid = None
    timeline = []
    deadline = time.time() + 60
    while time.time() < deadline:
        rows = ps_rows()
        clients = [r for r in rows if r["ProcessId"] not in before and
                   (r.get("Name") or "").lower() == "codomp_client_shipretail.exe"]
        if clients and pid is None:
            pid = clients[0]["ProcessId"]
        timeline.append({"at": iso(time.time()), "clients": [r["ProcessId"] for r in clients],
                         "ports": [p["local"] for p in port_rows()]})
        if pid is not None:
            break
        time.sleep(1.0)
    doc["launchTimeline"] = timeline
    doc["pid"] = pid
    if pid is None:
        doc["outcome"] = "ERROR: no client process appeared"
        (EVIDENCE / "stageD_run.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print("ERROR: no client appeared")
        return 1
    print("client pid:", pid)

    # ---- identity ----------------------------------------------------------
    exe_path = powershell("(Get-Process -Id " + str(pid) + " -ErrorAction Stop).Path").strip()
    doc["identity"] = {"pid": pid, "executablePath": exe_path,
                       "processCount": powershell("(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Measure-Object).Count").strip()}
    if exe_path and Path(exe_path).is_file():
        doc["identity"]["fileSha256"] = sha256(Path(exe_path))
        doc["identity"]["fileSize"] = Path(exe_path).stat().st_size
        doc["identity"]["fileVersion"] = powershell(
            "[System.Diagnostics.FileVersionInfo]::GetVersionInfo('" + exe_path + "').FileVersion").strip()
    print("identity:", json.dumps(doc["identity"], ensure_ascii=False))

    # ---- one attach --------------------------------------------------------
    sys.path.insert(0, str(RUNTIME))
    import CodolFridaRuntime  # noqa: E402
    doc["fridaTempDir"] = str(CodolFridaRuntime.configure_frida_runtime())
    import frida  # noqa: E402
    doc["fridaVersion"] = frida.__version__
    probe_src = PROBE_SOURCE.read_text(encoding="utf-8")
    control_src = CONTROL_SOURCE.read_text(encoding="utf-8")
    doc["sources"] = {"probe": {"path": str(PROBE_SOURCE), "sha256": sha256(PROBE_SOURCE)},
                      "control": {"path": str(CONTROL_SOURCE), "sha256": sha256(CONTROL_SOURCE),
                                  "lineCount": len(control_src.splitlines())}}
    raw_lines: list[str] = []

    def record(phase: str, message: dict) -> None:
        raw_lines.append(json.dumps({"at": iso(time.time()), "phase": phase, "message": message}, ensure_ascii=False))

    session = frida.get_local_device().attach(pid)
    doc["attach"] = {"ok": True, "at": iso(time.time()), "count": 1}
    detached: dict = {}
    session.on("detached", lambda *a: detached.update({"reason": str(a[0]) if a else None, "at": iso(time.time())}))

    def run_probe(phase_name: str):
        collected: list[dict] = []
        s = session.create_script(probe_src, name="t25_export_probe.js")
        s.on("message", lambda m, d: (collected.append(m), record(phase_name, m)))
        s.load()
        dl = time.time() + 10
        while time.time() < dl and not any(m.get("type") == "send" for m in collected):
            time.sleep(0.2)
        s.unload()
        return collected

    attempts = []
    payload = None
    for i in range(6):
        msgs = run_probe("probe-%d" % (i + 1))
        payload = next((m.get("payload") for m in msgs if m.get("type") == "send"), None)
        attempts.append({"attempt": i + 1, "at": iso(time.time()),
                         "pluginFound": (payload or {}).get("pluginFound"),
                         "moduleCount": (payload or {}).get("moduleCount"),
                         "requiredPresent": (payload or {}).get("requiredPresent")})
        print("  probe attempt", i + 1, "pluginFound=", (payload or {}).get("pluginFound"),
              "modules=", (payload or {}).get("moduleCount"),
              "requiredPresent=", (payload or {}).get("requiredPresent"))
        if payload and payload.get("pluginFound"):
            break
        time.sleep(4.0)
    doc["phase1"] = {"attempts": attempts, "payload": payload}
    doc["phase1ProbeMessages"] = "see stageD_frida_raw.jsonl"

    # ---- phase 2: the unmodified production control script -----------------
    if powershell("(Get-Process -Id " + str(pid) + " -ErrorAction SilentlyContinue | Measure-Object).Count").strip() == "1":
        control_messages: list[dict] = []
        t0 = time.time()
        s2 = session.create_script(control_src, name="generated_control_script.js")
        s2.on("message", lambda m, d: (control_messages.append(m), record("control", m)))
        s2.load()
        dl = time.time() + 30
        while time.time() < dl:
            if any(m.get("type") == "send" and isinstance(m.get("payload"), dict) and "result" in m["payload"]
                   for m in control_messages):
                break
            time.sleep(0.2)
        time.sleep(1.5)
        s2.unload()
        doc["phase2"] = {"durationS": round(time.time() - t0, 3), "messageCount": len(control_messages),
                         "messages": control_messages,
                         "statusPayload": next((m.get("payload") for m in control_messages
                                                if m.get("type") == "send" and isinstance(m.get("payload"), dict)
                                                and "result" in m["payload"]), None),
                         "errors": [m for m in control_messages if m.get("type") == "error"]}
        print("phase2 status:", json.dumps(doc["phase2"]["statusPayload"], ensure_ascii=False)[:1500])
        print("phase2 errors:", json.dumps(doc["phase2"]["errors"], ensure_ascii=False)[:600])
    else:
        doc["phase2"] = {"status": "SKIPPED", "reason": "client exited before phase 2"}

    doc["clientAliveAtDetach"] = powershell(
        "(Get-Process -Id " + str(pid) + " -ErrorAction SilentlyContinue | Measure-Object).Count").strip() == "1"
    session.detach()
    doc["detach"] = detached
    doc["afterDetach"] = {"ports": port_rows(), "at": iso(time.time()),
                          "clientAlive": powershell("(Get-Process -Id " + str(pid) +
                                                    " -ErrorAction SilentlyContinue | Measure-Object).Count").strip() == "1"}
    # new bootstrapper log lines
    if boot.is_file():
        text = boot.read_text(encoding="utf-8", errors="replace")
        doc["bootstrapperLogNew"] = text[boot_offset:]
    doc["endedAt"] = iso(time.time())
    (EVIDENCE / "stageD_frida_raw.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (EVIDENCE / "stageD_run.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("aliveAtDetach:", doc["clientAliveAtDetach"], "afterDetach:", doc["afterDetach"])
    print("bootstrapper new:", json.dumps(doc.get("bootstrapperLogNew", ""), ensure_ascii=False)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
