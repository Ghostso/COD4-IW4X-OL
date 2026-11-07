"""T-2.5 Stage 1: inventory the REAL generated control script.

Builds the exact source the tool would load (captured from create_script) and
reports its hooks, module lookups, required/optional exports and load order.
Read-only: nothing is attached.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

RUNTIME_DIR = Path(r"F:\桌面\ol\ol-mod-olfinal\tools\runtime")
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(RUNTIME_DIR))

if "CodolFridaRuntime" not in sys.modules:
    stub = types.ModuleType("CodolFridaRuntime")
    stub.configure_frida_runtime = lambda: RUNTIME_DIR  # type: ignore[attr-defined]
    sys.modules["CodolFridaRuntime"] = stub

import CodolGameServerControl as control  # noqa: E402


class FakeScript:
    def __init__(self, payload):
        self.payload = payload
        self.handlers = {}

    def on(self, event, handler):
        self.handlers[event] = handler

    def load(self):
        self.handlers["message"]({"type": "send", "payload": self.payload}, None)

    def unload(self):
        pass


def capture_source(argv):
    device = mock.Mock()
    device.enumerate_processes.return_value = [
        SimpleNamespace(pid=4242, name=control.TARGET_NAME)
    ]
    session = mock.Mock()
    session.create_script.return_value = FakeScript({
        "ok": True, "result": "confirmed", "pid": 4242, "action": "status",
        "before": {}, "after": {},
    })
    device.attach.return_value = session
    with (
        mock.patch.object(sys, "argv", ["CodolGameServerControl.py", *argv]),
        mock.patch.object(control.frida, "get_local_device", return_value=device),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        control.run()
    return session.create_script.call_args.args[0]


def main() -> int:
    source = capture_source(["--pid", "4242", "--sample-seconds", "0"])
    lines = source.splitlines()

    def find(pattern):
        return [(index + 1, line.strip()) for index, line in enumerate(lines)
                if re.search(pattern, line)]

    intercepts = find(r"Interceptor\.attach\(")
    native_required = [m.group(1) for m in re.finditer(r"nativeExport\(\s*plugin,\s*'([^']+)'", source)]
    plugin_exports = sorted(set(re.findall(r"plugin\.getExportByName\('([^']+)'\)", source)))
    exception_handlers = find(r"Process\.setExceptionHandler\(")
    identity_guard = find(r"attached process is not the CODOL client")
    plugin_lookup = find(r"Process\.findModuleByName\(")
    global_export_lookup = find(r"Module\.findExportByName\(null,")

    # The status() function's own export calls, in order.
    status_body = source.split("function status()", 1)[1].split("\n    }", 1)[0] if "function status()" in source else ""
    status_calls = re.findall(r"(\w+)\(([^)]*)\)", status_body)

    action_branches = find(r"if \(action === 'enable'|if \(action === 'disable'|const before = status\(\)")

    document = {
        "source_sha256_len": len(source),
        "source_lines": len(lines),
        "required_exports_via_nativeExport": native_required,
        "required_export_count": len(native_required),
        "optional_exports_via_try_catch": plugin_exports,
        "optional_export_count": len(plugin_exports),
        "interceptor_attach_sites": intercepts,
        "process_setExceptionHandler_sites": exception_handlers,
        "identity_guard_sites": identity_guard,
        "plugin_module_lookup_sites": plugin_lookup,
        "global_export_lookup_sites": global_export_lookup,
        "action_branch_sites": action_branches,
        "status_function_calls": status_calls,
        "load_order": [],
    }

    order = [
        ("identity guard (Process.enumerateModules()[0].name)", identity_guard[0][0] if identity_guard else None),
        ("plugin module lookup (Process.findModuleByName)", plugin_lookup[0][0] if plugin_lookup else None),
        ("nativeExport: CODOL_GameServerSetEnabled", next((i for i, l in enumerate(lines, 1) if "CODOL_GameServerSetEnabled" in l), None)),
        ("nativeExport: CODOL_GameServerGetTransportStatus", next((i for i, l in enumerate(lines, 1) if "CODOL_GameServerGetTransportStatus" in l), None)),
        ("Process.setExceptionHandler", exception_handlers[0][0] if exception_handlers else None),
        ("Module.findExportByName(null, ...) hook loop", global_export_lookup[0][0] if global_export_lookup else None),
        ("Interceptor.attach(termination exports)", intercepts[0][0] if intercepts else None),
        ("action branch (enable/disable/status)", action_branches[0][0] if action_branches else None),
    ]
    document["load_order"] = [{"step": name, "line": line} for name, line in order]

    (EVIDENCE / "control_script_inventory.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVIDENCE / "generated_control_script.js").write_text(source, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
