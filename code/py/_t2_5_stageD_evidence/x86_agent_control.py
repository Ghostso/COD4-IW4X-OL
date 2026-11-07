"""T-2.5 Stage D control experiment: is x86 (32-bit) frida-agent injection working here at all?

Spawns a harmless 32-bit process (SysWOW64 cmd.exe), attaches with the same Frida runtime
configuration used for the CODOL attempt, loads a trivial reporting script, then detaches
and terminates ONLY that harmless test process. No CODOL process is touched.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
RUNTIME = Path("F:/桌面/ol/ol-mod-olfinal/tools/runtime")
TZ = timezone(timedelta(hours=8))

PROBE = """(function () {
    send({ phase: 'control', pid: Process.id, arch: Process.arch, pointerSize: Process.pointerSize,
           moduleCount: Process.enumerateModules().length, frida: Frida.version,
           firstModule: Process.enumerateModules()[0].name });
})();"""


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0800"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    doc: dict = {"startedAt": iso(time.time()), "scope": "harmless 32-bit control process only; no CODOL process touched"}
    sys.path.insert(0, str(RUNTIME))
    import CodolFridaRuntime  # noqa: E402
    doc["fridaTempDir"] = str(CodolFridaRuntime.configure_frida_runtime())
    import frida  # noqa: E402
    doc["fridaVersion"] = frida.__version__

    cmd = r"C:\Windows\SysWOW64\cmd.exe"
    proc = subprocess.Popen([cmd, "/c", "ping -n 120 127.0.0.1 > nul"],
                            creationflags=subprocess.CREATE_NO_WINDOW)
    doc["control"] = {"path": cmd, "pid": proc.pid, "spawnedAt": iso(time.time())}
    time.sleep(2.0)

    is32 = subprocess.run(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(proc.pid) +
                           "').Name"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()
    doc["control"]["name"] = is32
    messages: list[dict] = []
    try:
        device = frida.get_local_device()
        session = device.attach(proc.pid)
        doc["attach"] = {"ok": True, "attachedAt": iso(time.time())}
        script = session.create_script(PROBE, name="t25_control_probe.js")
        script.on("message", lambda m, d: messages.append(m))
        script.load()
        deadline = time.time() + 10
        while time.time() < deadline and not any(m.get("type") == "send" for m in messages):
            time.sleep(0.2)
        script.unload()
        session.detach()
        doc["attach"]["detached"] = True
    except Exception as error:  # noqa: BLE001
        doc["attach"] = {"ok": False, "errorType": type(error).__name__, "error": str(error),
                         "failedAt": iso(time.time())}
    doc["messages"] = messages
    doc["payload"] = next((m.get("payload") for m in messages if m.get("type") == "send"), None)
    doc["verdict"] = "X86_AGENT_OK" if doc.get("payload") else "X86_AGENT_FAILED"

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    doc["control"]["terminated"] = True
    doc["endedAt"] = iso(time.time())
    (EVIDENCE / "x86_agent_control.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("fridaTempDir:", doc["fridaTempDir"])
    print("control pid:", proc.pid, "attach:", json.dumps(doc.get("attach"), ensure_ascii=False))
    print("payload:", json.dumps(doc["payload"], ensure_ascii=False))
    print("VERDICT:", doc["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
