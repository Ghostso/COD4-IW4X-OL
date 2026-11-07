"""T-2.4-C post-run integrity check: records the frozen-state comparison."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path(r"F:\桌面\ol\ol-mod-olfinal")
DCOPY = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal")
RESULTS = EVIDENCE / "T2_4C_RESULTS.json"

EXPECTED_T23 = {
    "tools/runtime/CodolGameServerControl.py":
        "DF7291F3CAE0EBD1CF415233A0FFF5A90EBE5106B79A20D167AA4DF8A9B5510E",
    "tools/runtime/CodolGame.py":
        "74892CDEEC889320994B1C867949C0F1DAADB84BFC3713A8E671438A1008D3EA",
    "tools/runtime/CodolGameTests.py":
        "D04479DD9AFB3FC1A72C0796C6AC1BF0C57FC16DFD8C12D7824D360CDA5E694D",
    "tools/runtime/CodolGameServerControlTests.py":
        "FF875F1683DA865BAC6D6E35A1080E4B748A12848C73106E96421702AA8362AC",
    "tools/runtime/requirements-codol.txt":
        "0AD4FB806C21DE958FA2F1E8705B21BF5B9D1F85DCE505965D226DC412763F2E",
    "config/codol-target-build.json":
        "B892F5C9D8B0F4DE40B14966459B4346BF934E1DE675D712F624E50D17F64F25",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def run(argv, cwd=None, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    return result.returncode, result.stdout.strip()


def main() -> int:
    integrity = {}

    code, head = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    integrity["head"] = head
    code, status = run(["git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"])
    integrity["status_entries"] = len([l for l in status.splitlines() if l.strip()])
    code, dstatus = run(["git", "-C", str(DCOPY), "status", "--porcelain=v1", "--untracked-files=all"])
    integrity["dcopy_status_entries"] = len([l for l in dstatus.splitlines() if l.strip()])

    stage = ROOT / "build" / "stage"
    integrity["stage_mtime"] = stage.stat().st_mtime if stage.exists() else None

    files = {}
    for relative, expected in EXPECTED_T23.items():
        actual = sha256(ROOT / relative)
        files[relative] = {"expected": expected, "actual": actual, "unchanged": actual == expected}
    integrity["t23_files"] = files
    integrity["t23_all_unchanged"] = all(item["unchanged"] for item in files.values())

    # Process facts. The marker is assembled at runtime so this very command line
    # cannot match itself.
    marker = "probe" + "_host" + ".py"
    # NOTE 1: $host is a PowerShell automatic variable; assigning to it silently
    # does nothing, so every local here uses a non-reserved name.
    # NOTE 2: the marker is passed through the environment, not interpolated into the
    # script text, so the query cannot match its own command line.
    ps = (
        "$hostCount = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.CommandLine -like ('*' + $env:T24C_MARKER + '*') }).Count; "
        "$gameCount = @(Get-Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ProcessName -match 'codoMP|ol_room_owner|CodolGameServer|Injector32' }).Count; "
        "$fridaCount = @(Get-Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ProcessName -match 'frida' }).Count; "
        "$udpCount = @(netstat -ano -p UDP 2>$null | Select-String -Pattern ':2896[0-2]|:28970').Count; "
        "$goneFlag = if (Get-Process -Id " + str(json.loads(RESULTS.read_text(encoding='utf-8'))['host']['spawned_pid']) + " -ErrorAction SilentlyContinue) { 'no' } else { 'yes' }; "
        "Write-Output ([string]$hostCount + '|' + [string]$gameCount + '|' + [string]$fridaCount + '|' + [string]$udpCount + '|' + $goneFlag)"
    )
    environment = dict(os.environ, T24C_MARKER=marker)
    code, out = run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        env=environment,
    )
    parts = (out.splitlines()[-1] if out else "?|?|?|?|?").split("|")
    integrity["host_process_remnants"] = int(parts[0]) if parts[0].isdigit() else None
    integrity["game_processes"] = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    integrity["frida_processes"] = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
    integrity["game_port_listeners"] = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
    integrity["host_pid_gone"] = (len(parts) > 4 and parts[4].strip() == "yes")

    integrity["no_codol_touched"] = (
        integrity["game_processes"] == 0
        and integrity["game_port_listeners"] == 0
        and integrity["host_process_remnants"] == 0
        and integrity["host_pid_gone"] is True
    )

    document = json.loads(RESULTS.read_text(encoding="utf-8"))
    document["integrity"] = integrity
    statuses = {case["id"]: case["status"] for case in document.get("cases", [])}
    document["case_statuses"] = statuses
    if all(status == "PASS" for status in statuses.values()) and integrity["t23_all_unchanged"] and integrity["no_codol_touched"]:
        document["verdict"] = "A. Stage C 通过"
    elif any(status == "PASS" for status in statuses.values()):
        document["verdict"] = "B. Stage C 有条件通过"
    else:
        document["verdict"] = "C. Stage C 不通过"
    RESULTS.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"integrity": integrity, "verdict": document["verdict"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
