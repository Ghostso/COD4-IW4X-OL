"""T-2.5 Stage D: ONE Frida attach to the live sandbox client.

Phase 1 loads a read-only export probe (no hooks, no game-memory reads, no plugin calls).
Phase 2 loads the UNMODIFIED generated control script that CodolGameServerControl.py would
load, captured from the tool itself. The control-script SHA-256 is recorded so the byte
identity is verifiable.

The client is never terminated; no setEnabled call is made; no port probe is performed.
"""
from __future__ import annotations

import hashlib
import json
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
TZ = timezone(timedelta(hours=8))


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0800"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def powershell(script: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False).stdout


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
            rows.append({"protocol": parts[0].upper(), "local": local, "state": parts[3], "ownerPid": parts[-1]})
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    pid = int(sys.argv[1])
    doc: dict = {"scope": "1 Frida attach; phase1 probe + phase2 production control script; client not terminated",
                 "pid": pid, "startedAt": iso(time.time())}

    # D1 identity
    info = powershell("$p=Get-Process -Id " + str(pid) + " -ErrorAction SilentlyContinue; "
                      "if ($p) { $p | Select-Object Id,ProcessName,StartTime,Responding,Path | ConvertTo-Json -Compress }")
    doc["identity"] = {"powershell": info.strip()}
    path = powershell("(Get-Process -Id " + str(pid) + " -ErrorAction Stop).Path")
    exe_path = path.strip()
    doc["identity"]["executablePath"] = exe_path
    if exe_path and Path(exe_path).is_file():
        doc["identity"]["fileSha256"] = sha256(Path(exe_path))
        doc["identity"]["fileSize"] = Path(exe_path).stat().st_size
        doc["identity"]["fileVersion"] = powershell(
            "[System.Diagnostics.FileVersionInfo]::GetVersionInfo('" + exe_path + "').FileVersion").strip()
    count = powershell("(Get-Process -Name codoMP_client_shipRetail -ErrorAction SilentlyContinue | Measure-Object).Count")
    doc["identity"]["processCount"] = count.strip()
    doc["beforeAttach"] = {"ports": port_rows(), "at": iso(time.time())}

    sys.path.insert(0, str(RUNTIME))
    import CodolFridaRuntime  # noqa: E402
    doc["fridaTempDir"] = str(CodolFridaRuntime.configure_frida_runtime())
    import frida  # noqa: E402
    doc["fridaVersion"] = frida.__version__

    doc["sources"] = {"probe": {"path": str(PROBE_SOURCE), "sha256": sha256(PROBE_SOURCE)},
                      "control": {"path": str(CONTROL_SOURCE), "sha256": sha256(CONTROL_SOURCE)}}
    control_src = CONTROL_SOURCE.read_text(encoding="utf-8")
    probe_src = PROBE_SOURCE.read_text(encoding="utf-8")
    doc["controlScriptLineCount"] = len(control_src.splitlines())

    raw = EVIDENCE / "stageD_frida_raw.jsonl"
    raw_lines = []

    def record(phase: str, message: dict) -> None:
        raw_lines.append(json.dumps({"at": iso(time.time()), "phase": phase, "message": message},
                                    ensure_ascii=False))

    device = frida.get_local_device()
    session = device.attach(pid)
    doc["attach"] = {"ok": True, "at": iso(time.time())}
    detached = {}
    session.on("detached", lambda *a: detached.update({"reason": a[0] if a else None,
                                                       "at": iso(time.time())}))

    # phase 1
    probe_messages: list[dict] = []
    script = session.create_script(probe_src, name="t25_export_probe.js")
    script.on("message", lambda m, d: (probe_messages.append(m), record("probe", m)))
    t0 = time.time()
    script.load()
    deadline = time.time() + 15
    while time.time() < deadline and not any(m.get("type") == "send" for m in probe_messages):
        time.sleep(0.2)
    script.unload()
    doc["phase1"] = {"durationS": round(time.time() - t0, 3), "messages": probe_messages,
                     "payload": next((m.get("payload") for m in probe_messages if m.get("type") == "send"), None)}

    # phase 2
    control_messages: list[dict] = []
    t1 = time.time()
    script2 = session.create_script(control_src, name="generated_control_script.js")
    script2.on("message", lambda m, d: (control_messages.append(m), record("control", m)))
    script2.load()
    deadline = time.time() + 25
    while time.time() < deadline:
        if any(m.get("type") == "send" and isinstance(m.get("payload"), dict)
               and "result" in m["payload"] for m in control_messages):
            break
        time.sleep(0.2)
    time.sleep(1.0)
    script2.unload()
    doc["phase2"] = {"durationS": round(time.time() - t1, 3), "messageCount": len(control_messages),
                     "messages": control_messages,
                     "statusPayload": next((m.get("payload") for m in control_messages
                                            if m.get("type") == "send" and isinstance(m.get("payload"), dict)
                                            and "result" in m["payload"]), None),
                     "errors": [m for m in control_messages if m.get("type") == "error"]}

    alive = powershell("(Get-Process -Id " + str(pid) + " -ErrorAction SilentlyContinue | Measure-Object).Count").strip()
    doc["clientAliveAfterPhase2"] = alive == "1"
    session.detach()
    doc["detach"] = detached
    doc["afterDetach"] = {"ports": port_rows(), "at": iso(time.time()),
                          "clientAlive": powershell("(Get-Process -Id " + str(pid) +
                                                    " -ErrorAction SilentlyContinue | Measure-Object).Count").strip() == "1"}
    doc["endedAt"] = iso(time.time())
    raw.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (EVIDENCE / "stageD_attach.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "identity": doc["identity"],
        "attach": doc["attach"],
        "phase1_messages": len(probe_messages),
        "phase1_payload": doc["phase1"]["payload"],
        "phase2_messageCount": len(control_messages),
        "phase2_statusPayload": doc["phase2"]["statusPayload"],
        "phase2_errors": doc["phase2"]["errors"],
        "clientAliveAfterPhase2": doc["clientAliveAfterPhase2"],
        "detach": detached,
        "afterDetach": doc["afterDetach"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
