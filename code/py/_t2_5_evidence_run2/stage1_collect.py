"""T-2.5 Stage 1 (fresh run): read-only environment + target precheck.

Every fact is produced by an actual command in this run. Nothing is attached,
started, injected, read from a CODOL process, or terminated.
Writes only into its own evidence directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path(r"F:\桌面\ol\ol-mod-olfinal")
RUNTIME = ROOT / "tools" / "runtime"
STAGE = ROOT / "build" / "stage"
GAME = Path(r"E:\CODOL_SANDBOX\RUN001")
DCOPY = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal")
PY = sys.executable
TZ = timezone(timedelta(hours=8))
PORTS = (28960, 28961, 28962, 28970)

records: list[dict] = []


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def run(label: str, argv: list[str], cwd: Path | None = None, timeout: int = 900) -> dict:
    started = time.time()
    try:
        proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)
        code, out, err, timedout = proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        code, out, err, timedout = None, exc.stdout or "", exc.stderr or "", True
    rec = {
        "label": label,
        "argv": argv,
        "cwd": str(cwd) if cwd else None,
        "startedAt": iso(started),
        "endedAt": iso(time.time()),
        "durationS": round(time.time() - started, 3),
        "returncode": code,
        "timedOut": timedout,
        "stdout": out,
        "stderr": err,
    }
    records.append(rec)
    safe = label.replace("/", "_").replace(" ", "_")
    (EVIDENCE / f"raw_{safe}.log").write_text(
        "ARGV: " + json.dumps(argv, ensure_ascii=False) + "\n"
        "CWD: " + str(cwd) + "\n"
        "START: " + rec["startedAt"] + "\nEND: " + rec["endedAt"] + "\n"
        "EXIT: " + str(code) + ("  TIMEOUT" if timedout else "") + "\n"
        "--- STDOUT ---\n" + out + "\n--- STDERR ---\n" + err + "\n",
        encoding="utf-8")
    return rec


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def try_bind(address: str, port: int, export: dict) -> dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    row = {"address": address, "port": port}
    try:
        sock.bind((address, port))
        row.update(bound=True, error=None, errno=None, winerror=None)
        export.append(row["address"] + ":" + str(port))
    except OSError as error:
        row.update(bound=False, error=error.strerror, errno=error.errno,
                   winerror=getattr(error, "winerror", None))
    finally:
        sock.close()
    return row


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    result: dict = {"stage": "1", "runStartedAt": iso(time.time())}

    # ---- A. environment -------------------------------------------------
    import frida  # noqa: F401
    import importlib.metadata as md
    result["environment"] = {
        "pythonVersion": sys.version.split()[0],
        "pythonExecutable": sys.executable,
        "fridaVersion": frida.__version__,
        "fridaToolsVersion": md.version("frida-tools"),
        "host": os.environ.get("COMPUTERNAME"),
        "evidenceDir": str(EVIDENCE),
        "collectedAt": iso(time.time()),
    }

    # ---- B. worktree state ---------------------------------------------
    branch = run("git.branch", ["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"])
    head = run("git.head", ["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    status = run("git.status", ["git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"])
    entries = [l for l in status["stdout"].splitlines() if l.strip()]
    log5 = run("git.log5", ["git", "-C", str(ROOT), "log", "--oneline", "-5"])
    result["worktree"] = {
        "path": str(ROOT),
        "branch": branch["stdout"].strip(),
        "head": head["stdout"].strip(),
        "statusEntries": len(entries),
        "statusEntriesList": entries,
        "modifiedTracked": len([e for e in entries if e[:2].strip() == "M"]),
        "untracked": len([e for e in entries if e.startswith("??")]),
        "log5": log5["stdout"].strip().splitlines(),
        "stageMtime": iso(STAGE.stat().st_mtime) if STAGE.exists() else None,
    }
    dstatus = run("git.Dcopy.status",
                  ["git", "-C", str(DCOPY), "status", "--porcelain=v1", "--untracked-files=all"])
    dhead = run("git.Dcopy.head", ["git", "-C", str(DCOPY), "rev-parse", "HEAD"])
    result["dcopy"] = {
        "path": str(DCOPY),
        "exists": DCOPY.is_dir(),
        "head": dhead["stdout"].strip(),
        "statusEntries": len([l for l in dstatus["stdout"].splitlines() if l.strip()]),
        "note": "read-only: git queries only, no write of any kind",
    }

    # ---- C. frozen hashes ----------------------------------------------
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
    EXTRA = {
        "src/game_server/FrameHook.cpp": "1CA962D707F23DA40F60878DB5A8542601BA68398FE4EA226D0F957BE8008D8A",
    }
    def group(table: dict) -> dict:
        out = {}
        for rel, expected in table.items():
            path = ROOT / rel
            actual = sha256(path) if path.is_file() else None
            out[rel] = {"expected": expected, "actual": actual,
                        "unchanged": actual == expected,
                        "size": path.stat().st_size if path.is_file() else None}
        return out
    t23, t1, extra = group(T23), group(T1), group(EXTRA)
    result["integrity"] = {
        "t23": t23, "t23AllUnchanged": all(v["unchanged"] for v in t23.values()),
        "t1": t1, "t1AllUnchanged": all(v["unchanged"] for v in t1.values()),
        "t2AcceptanceForbiddenArea": extra,
        "extraAllUnchanged": all(v["unchanged"] for v in extra.values()),
        "provenance": "expected values transcribed from T2_3_SHA256_MANIFEST.txt and T2_ACCEPTANCE_SHA256_MANIFEST.txt",
    }

    # ---- D. target identity (file level) --------------------------------
    exe = GAME / "codoMP_client_shipRetail.exe"
    plugin = GAME / "Ayria" / "Plugins" / "CodolGameServer.Localnet32"
    target: dict = {"path": str(exe)}
    if exe.is_file():
        stat = exe.stat()
        target.update(exists=True, size=stat.st_size, mtimeLocal=iso(stat.st_mtime),
                      sha256=sha256(exe))
    else:
        target["exists"] = False
    ver = run("target.version",
              ["powershell", "-NoProfile", "-Command",
               f"$v=[System.Diagnostics.FileVersionInfo]::GetVersionInfo('{exe}');"
               " Write-Output \"FileVersion=$($v.FileVersion)\";"
               " Write-Output \"ProductVersion=$($v.ProductVersion)\";"
               " Write-Output \"CompanyName=$($v.CompanyName)\";"
               " Write-Output \"FileDescription=$($v.FileDescription)\""])
    machine = run("target.machine",
                  ["powershell", "-NoProfile", "-Command",
                   f"$fs=[System.IO.File]::OpenRead('{exe}');"
                   " $br=New-Object System.IO.BinaryReader($fs);"
                   " $fs.Position=0x3C; $pe=$br.ReadInt32(); $fs.Position=$pe+4;"
                   " $m=$br.ReadUInt16(); $fs.Close();"
                   " Write-Output ('machine=0x{0:x4}' -f $m)"])
    target["versionInfoRaw"] = ver["stdout"].strip()
    target["computeMachine"] = machine["stdout"].strip()
    target["fileVersion"] = next((l.split("=", 1)[1] for l in ver["stdout"].splitlines()
                                  if l.startswith("FileVersion=")), None)
    plug: dict = {"path": str(plugin)}
    if plugin.is_file():
        pstat = plugin.stat()
        plug.update(exists=True, size=pstat.st_size, sha256=sha256(plugin))
    else:
        plug["exists"] = False
    result["target"] = {"client": target, "plugin": plug,
                        "gameDirIsDir": GAME.is_dir(),
                        "outExePresent": (GAME / "out.exe").exists()}

    # ---- E. process scan -------------------------------------------------
    ps = run("process.scan", ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress"])
    procs = []
    try:
        procs = json.loads(ps["stdout"])
        if isinstance(procs, dict):
            procs = [procs]
    except Exception as error:  # pragma: no cover
        result["processScanError"] = str(error)
    name_re = ("codo", "ol_room_owner", "injector32", "olgs", "codol")
    matches = []
    for entry in procs:
        name = (entry.get("Name") or "").lower()
        path = (entry.get("ExecutablePath") or "")
        if any(token in name for token in name_re) or "CODOL_SANDBOX" in path.upper():
            matches.append(entry)
    result["processes"] = {
        "totalProcesses": len(procs),
        "matchRule": "Name contains codo|ol_room_owner|injector32|olgs|codol, or ExecutablePath contains CODOL_SANDBOX",
        "matches": matches,
        "matchCount": len(matches),
    }
    (EVIDENCE / "raw_process_table.json").write_text(
        json.dumps(procs, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- F. ports --------------------------------------------------------
    net = run("ports.netstat", ["netstat", "-ano"])
    rows = []
    for line in net["stdout"].splitlines():
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
    export: list[str] = []
    binds = [try_bind(addr, port, export) for port in PORTS for addr in ("0.0.0.0", "127.0.0.1")]
    result["ports"] = {"osEndpoints": rows, "transientBind": binds,
                       "note": "SO_REUSEADDR deliberately NOT set; each probe binds and closes immediately"}

    # ---- G/H/I. tool-driven evidence ------------------------------------
    verify = run("tool.verify-target",
                 [PY, str(RUNTIME / "CodolGame.py"), "verify-target", "--game-dir", str(GAME)])
    try:
        result["verifyTarget"] = json.loads(verify["stdout"])
    except Exception:
        result["verifyTarget"] = {"parseError": True, "raw": verify["stdout"]}
    result["verifyTargetExitCode"] = verify["returncode"]

    plugin_ex = run("tool.plugin-exports", [PY, str(EVIDENCE / "plugin_exports.py")])
    result["pluginExportRun"] = {"returncode": plugin_ex["returncode"]}
    inventory = run("tool.script-inventory", [PY, str(EVIDENCE / "script_analysis.py")])
    result["scriptInventoryRun"] = {"returncode": inventory["returncode"]}
    for name, key in (("plugin_export_table.json", "pluginExportTable"),
                      ("control_script_inventory.json", "controlScriptInventory")):
        path = EVIDENCE / name
        result[key] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    # ---- J. regression suites -------------------------------------------
    tool_tests = run("tests.tool", [PY, "CodolGameServerControlTests.py", "-v"], cwd=RUNTIME)
    caller_tests = run("tests.caller", [PY, "CodolGameTests.py", "-v"], cwd=RUNTIME)
    def summary(rec: dict) -> dict:
        lines = [l for l in (rec["stdout"] + rec["stderr"]).splitlines()
                 if l.startswith(("Ran ", "OK", "FAILED"))]
        return {"returncode": rec["returncode"], "summaryLines": lines}
    result["tests"] = {"tool": summary(tool_tests), "caller": summary(caller_tests)}

    # ---- K. T-1 C++ regression artifacts ---------------------------------
    stage_files = sorted(p.name for p in STAGE.iterdir()) if STAGE.is_dir() else []
    result["stageDir"] = {"path": str(STAGE), "exists": STAGE.is_dir(), "fileCount": len(stage_files),
                          "testExes": [n for n in stage_files if "test" in n.lower() and n.lower().endswith(".exe")]}
    t1exe = STAGE / "ol_transport_lifecycle_tests.exe"
    if t1exe.is_file():
        t1run = run("tests.T1.transport", [str(t1exe)])
        tail = [l for l in t1run["stdout"].splitlines() if l.strip()][-6:]
        result["tests"]["t1Transport"] = {"path": str(t1exe), "sha256": sha256(t1exe),
                                          "returncode": t1run["returncode"], "tail": tail}
    else:
        result["tests"]["t1Transport"] = {"status": "SKIPPED", "reason": f"not present: {t1exe}"}

    result["runFinishedAt"] = iso(time.time())
    result["records"] = records
    (EVIDENCE / "stage1_evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "worktree": {k: result["worktree"][k] for k in ("branch", "head", "statusEntries", "stageMtime")},
        "integrity": {"t23AllUnchanged": result["integrity"]["t23AllUnchanged"],
                      "t1AllUnchanged": result["integrity"]["t1AllUnchanged"],
                      "extraAllUnchanged": result["integrity"]["extraAllUnchanged"]},
        "target": result["target"],
        "verifyTargetExitCode": result["verifyTargetExitCode"],
        "verifyTargetOk": result["verifyTarget"].get("ok"),
        "processMatchCount": result["processes"]["matchCount"],
        "ports": {"osEndpoints": len(rows), "allBindable": all(b["bound"] for b in binds)},
        "plugin": {k: result["pluginExportTable"][k] for k in
                   ("required_present_count", "required_missing", "machine", "export_count", "codol_export_count")},
        "script": {k: result["controlScriptInventory"][k] for k in
                   ("source_lines", "required_export_count", "optional_export_count",
                    "interceptor_attach_sites", "process_setExceptionHandler_sites",
                    "action_branch_sites")},
        "tests": result["tests"],
        "stageDir": result["stageDir"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
