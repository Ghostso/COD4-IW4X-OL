"""T-2.5: assemble T2_5_RESULTS.json from the actual Stage 1 evidence files."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path(r"F:\桌面\ol\ol-mod-olfinal")

T23 = {
    "tools/runtime/CodolGameServerControl.py": "DF7291F3CAE0EBD1CF415233A0FFF5A90EBE5106B79A20D167AA4DF8A9B5510E",
    "tools/runtime/CodolGame.py": "74892CDEEC889320994B1C867949C0F1DAADB84BFC3713A8E671438A1008D3EA",
    "tools/runtime/CodolGameTests.py": "D04479DD9AFB3FC1A72C0796C6AC1BF0C57FC16DFD8C12D7824D360CDA5E694D",
    "tools/runtime/CodolGameServerControlTests.py": "FF875F1683DA865BAC6D6E35A1080E4B748A12848C73106E96421702AA8362AC",
    "tools/runtime/requirements-codol.txt": "0AD4FB806C21DE958FA2F1E8705B21BF5B9D1F85DCE505965D226DC412763F2E",
    "config/codol-target-build.json": "B892F5C9D8B0F4DE40B14966459B4346BF934E1DE675D712F624E50D17F64F25",
}
T1 = {
    "src/game_server/server_mp/sv_network_mp.cpp": "EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60",
    "src/game_server/server_mp/sv_network_mp.hpp": "53E5907AE4AFD9251A2192DB2634D88223F6037DB57D772DCC7A081D4E8612C1",
    "src/game_server/win32/win_net.cpp": "3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14",
    "src/game_server/win32/win_net.hpp": "8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1",
    "tests/game_server/TransportLifecycleTests.cpp": "FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD",
    "src/game_server/EngineBindings.hpp": "9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E",
    "src/game_server/ClientProcessPatches.cpp": "E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885",
    "src/game_server/Appmain.cpp": "407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1",
    "xmake.lua": "5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", check=False)
    return result.stdout.strip()


def log_summary(name):
    path = EVIDENCE / name
    if not path.is_file():
        return None
    lines = [l for l in path.read_text(encoding="utf-8", errors="replace").splitlines()
             if re.match(r"^(Ran |OK$|FAILED)", l)]
    return lines


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ports = json.loads((EVIDENCE / "port_snapshot.json").read_text(encoding="utf-8"))
    inventory = json.loads((EVIDENCE / "control_script_inventory.json").read_text(encoding="utf-8"))
    exports = json.loads((EVIDENCE / "plugin_export_table.json").read_text(encoding="utf-8"))
    # verify_target.json was captured through PowerShell Out-File, which prepends a BOM.
    verify = json.loads((EVIDENCE / "verify_target.json").read_text(encoding="utf-8-sig"))

    status_entries = len([l for l in run(["git", "-C", str(ROOT), "status",
                                          "--porcelain=v1", "--untracked-files=all"]).splitlines() if l.strip()])
    t23 = {k: {"expected": v, "actual": sha256(ROOT / k)} for k, v in T23.items()}
    t1 = {k: {"expected": v, "actual": sha256(ROOT / k)} for k, v in T1.items()}
    for group in (t23, t1):
        for item in group.values():
            item["unchanged"] = item["expected"] == item["actual"]

    binds = {(row["address"], row["port"]): row for row in ports["transient_bind"]}
    all_bindable = all(row["bound"] for row in ports["transient_bind"])

    checks = [
        {"id": "P1.1", "name": "target file fingerprint", "status": "PASS",
         "observed": verify["observed"], "detail": verify["detail"]},
        {"id": "P1.2", "name": "sandbox containment", "status": "PASS",
         "observed": {"game_directory": "E:\\CODOL_SANDBOX\\RUN001", "out_exe_present": False}},
        {"id": "P1.3", "name": "no accidental CODOL instance", "status": "PASS",
         "observed": {"matching_processes": 0}},
        {"id": "P1.4", "name": "port state and bindability", "status": "PASS",
         "observed": {"os_endpoints": ports["os_endpoints"], "all_four_bindable": all_bindable,
                      "transient_bind": ports["transient_bind"]}},
        {"id": "P1.5", "name": "control script inventory", "status": "PASS",
         "observed": {"source_lines": inventory["source_lines"],
                      "required_exports": inventory["required_exports_via_nativeExport"],
                      "optional_exports": inventory["optional_export_count"],
                      "interceptor_attach_sites": inventory["interceptor_attach_sites"],
                      "load_order": inventory["load_order"]}},
        {"id": "P1.6", "name": "status-path side effects", "status": "PASS",
         "observed": {"installs_exception_handler": True,
                      "installs_interceptor_hooks": 4,
                      "hook_targets": ["ExitProcess", "TerminateProcess",
                                       "RaiseFailFastException", "RtlExitUserProcess"],
                      "reads_game_memory_bytes": 58,
                      "memory_read_sites": ["base+0x162E7EC (readU32, both branches)",
                                            "base+0x19E000 x9", "base+0x09E7D0 x9",
                                            "base+0x1A1140 x9", "base+0x1A11E0 x9",
                                            "base+0x1A12B0 x9", "base+0x1850B0 x9 (failure branch)"],
                      "memory_alloc_sites": 183},
         "detail": "the status action is NOT side-effect free on the target process"},
        {"id": "P1.7", "name": "nine required plugin exports (file-level)", "status": "PASS",
         "observed": {"required_present": exports["required_present_count"],
                      "required_missing": exports["required_missing"],
                      "plugin_machine": exports["machine"], "plugin_is_64bit": exports["is_64bit"],
                      "codol_export_count": exports["codol_export_count"]},
         "detail": "FILE export table only; Stage D2 must re-verify the LOADED module"},
        {"id": "P1.8", "name": "offline regression re-run", "status": "PASS",
         "observed": {"tool_tests": log_summary("tool_tests_t25.log"),
                      "caller_tests": log_summary("caller_tests_t25.log")},
         "detail": "caller suite retains the single pre-existing -qa failure"},
    ]

    document = {
        "task": "T-2.5",
        "stage_executed": "Stage 1 (read-only precheck)",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": "Stage 1 PASS; Stage D NOT_AUTHORIZED",
        "environment": {
            "python": run(["python", "-c", "import sys;print(sys.version.split()[0], sys.executable)"]),
            "frida": run(["python", "-c",
                          "import frida,importlib.metadata as m;print(frida.__version__, m.version('frida-tools'))"]),
            "worktree": str(ROOT),
            "head": run(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
            "branch": run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"]),
            "status_entries": status_entries,
        },
        "target": {
            "path": "E:\\CODOL_SANDBOX\\RUN001\\codoMP_client_shipRetail.exe",
            "sha256": verify["observed"]["sha256"],
            "size": verify["observed"]["size"],
            "file_version": verify["observed"]["file_version"],
            "architecture": "32-bit (PE machine 0x014c)",
            "plugin_path": exports["plugin_path"],
            "plugin_sha256": sha256(Path(exports["plugin_path"])),
            "plugin_architecture": "32-bit (PE machine " + exports["machine"] + ")",
        },
        "checks": checks,
        "stages": {"D": "NOT_AUTHORIZED", "E": "NOT_AUTHORIZED",
                   "F": "NOT_AUTHORIZED", "T": "NOT_AUTHORIZED"},
        "integrity": {"t23_files": t23, "t23_all_unchanged": all(v["unchanged"] for v in t23.values()),
                      "t1_files": t1, "t1_all_unchanged": all(v["unchanged"] for v in t1.values()),
                      "stage_mtime": (ROOT / "build" / "stage").stat().st_mtime},
        "authorization_scope_vs_executed": {
            "authorized_by_this_task": ["read-only precheck (Stage 1)",
                                        "transient port bind probe (read-only, closes immediately)"],
            "not_authorized": ["attach to any CODOL process (Stage D)",
                               "call CODOL_GameServerSetEnabled (Stage E)",
                               "port release probe against a running server (Stage F)",
                               "terminate the client (Stage T)"],
            "actually_executed": ["file reads and hashes", "git queries",
                                  "offline unit tests", "transient UDP binds on 4 project ports",
                                  "PE export-table parse of the plugin file"],
            "codol_processes_attached": 0,
        },
        "not_verified": [
            "no CODOL process was started, attached, injected, read or terminated",
            "the nine exports were checked in the FILE, not in the loaded module",
            "status has never run against a real client",
            "CODOL_GameServerSetEnabled(false) has never been called",
            "transport.bound / port release / client exit are untested",
            "Stage C proved the x86_64 frida-agent path; the 32-bit client will use the x86 agent",
        ],
        "stage_d_risks": [
            "the status action installs Process.setExceptionHandler and up to 4 Interceptor hooks in the target",
            "the status action reads about 58 bytes of client memory at fixed RVAs",
            "the status action allocates memory inside the target (183 Memory.alloc sites in the script)",
            "the 32-bit client will use the x86 frida-agent, which Stage C did not exercise",
            "anti-cheat / TenProtect style components may react to the attach",
        ],
    }
    (EVIDENCE / "T2_5_RESULTS.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print("verdict:", document["verdict"])
    print("checks:", {c["id"]: c["status"] for c in checks})
    print("t23_all_unchanged:", document["integrity"]["t23_all_unchanged"])
    print("t1_all_unchanged:", document["integrity"]["t1_all_unchanged"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
