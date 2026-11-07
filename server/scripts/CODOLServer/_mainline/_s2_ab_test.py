# -*- coding: utf-8 -*-
"""Clean A/B test for the iips.dll LocalRM surgery.

Variant A = current sandbox iips.dll (E2367C48...).
Variant B = pristine baseline iips.dll (72DDB9D1...).

Only the sandbox IIPS\\iips.dll is changed. System networking, DNS,
routes, firewall rules and adapters are never touched.

Elevated usage:
  python -X utf8 _s2_ab_test.py prepare A
  powershell -NoProfile -ExecutionPolicy Bypass -File ..\\..\\run_codol_001\\run_direct_iips1_elevated.ps1 -Sandbox ..\\..\\run_codol_001\\sandbox_ifs1_20260923 -DurationSeconds 130 -RunDir ..\\..\\run_codol_001\\runs\\AB_A
  python -X utf8 _s2_ab_test.py analyze A ..\\..\\run_codol_001\\runs\\AB_A
  python -X utf8 _s2_ab_test.py prepare B
  ...
  python -X utf8 _s2_ab_test.py restore

Header comments stay ASCII on purpose.
"""
import ctypes
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RUNROOT = os.path.join(ROOT, "run_codol_001")
BASELINE = os.path.join(ROOT, "\u5de5\u5177", "EX035_DIR", "IIPS", "iips.dll")
SANDBOX = os.path.join(RUNROOT, "sandbox_ifs1_20260923")
SANDBOX_IIPS = os.path.join(SANDBOX, "IIPS", "iips.dll")
HOSTPID = os.path.join(SANDBOX, "IIPS", "HostPid")
STATE = os.path.join(HERE, "_s2_ab_state.json")
BACKUP = SANDBOX_IIPS + ".s2backup"
GAME_EXE = os.path.join(SANDBOX, "codoMP_client_shipRetail.exe")

BASELINE_SHA = "72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348"
PATCHED_SHA = "E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def read_hostpid():
    try:
        raw = open(HOSTPID, "rb").read()
        return {
            "exists": True,
            "length": len(raw),
            "hex": raw.hex(),
            "utf16": raw.decode("utf-16le", "replace").strip("\x00\r\n "),
            "ascii": raw.decode("ascii", "replace").strip("\r\n\x00 "),
        }
    except FileNotFoundError:
        return {"exists": False, "length": 0, "hex": "", "utf16": "", "ascii": ""}
    except Exception as exc:
        return {"exists": True, "error": repr(exc)}


def list_iips_pipes():
    names = []
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstFileW
    find_first.argtypes = [wintypes.LPCWSTR,
                           ctypes.POINTER(wintypes.WIN32_FIND_DATAW)]
    find_first.restype = wintypes.HANDLE
    find_next = kernel32.FindNextFileW
    find_next.argtypes = [wintypes.HANDLE,
                          ctypes.POINTER(wintypes.WIN32_FIND_DATAW)]
    find_next.restype = wintypes.BOOL
    find_close = kernel32.FindClose
    find_close.argtypes = [wintypes.HANDLE]
    data = wintypes.WIN32_FIND_DATAW()
    handle = find_first("\\\\.\\pipe\\*", ctypes.byref(data))
    if handle == wintypes.HANDLE(-1).value:
        return names
    try:
        while True:
            low = data.cFileName.lower()
            if "iips" in low or "tenio" in low or "tcls" in low:
                names.append(data.cFileName)
            if not find_next(handle, ctypes.byref(data)):
                break
    finally:
        find_close(handle)
    return sorted(set(names))


def process_rows():
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'codoMP|IIPS|TQMCenter|TP3Helper' } | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | "
        "ConvertTo-Json -Compress"
    )
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True, text=True, errors="replace"
    )
    text = proc.stdout.strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except Exception:
        return [{"raw": text}]
    return value if isinstance(value, list) else [value]


def kill_experiment_processes():
    for name in ("codoMP_client_shipRetail.exe", "IIPSHostApp.exe",
                 "TQMCenter.exe", "TP3Helper.exe"):
        subprocess.run(["taskkill", "/F", "/IM", name, "/T"],
                       capture_output=True, text=True)


def ensure_safe_paths():
    if not os.path.isfile(BASELINE):
        raise SystemExit("baseline missing: " + BASELINE)
    if not os.path.isfile(SANDBOX_IIPS):
        raise SystemExit("sandbox iips.dll missing: " + SANDBOX_IIPS)
    if not os.path.isfile(GAME_EXE):
        raise SystemExit("game executable missing: " + GAME_EXE)
    root = os.path.abspath(ROOT) + os.sep
    for path in (BASELINE, SANDBOX_IIPS, BACKUP):
        if not os.path.abspath(path).startswith(root):
            raise SystemExit("refusing path outside project: " + path)


def cmd_prepare(variant):
    variant = variant.upper()
    ensure_safe_paths()
    current = sha(SANDBOX_IIPS)
    if not os.path.exists(BACKUP):
        shutil.copy2(SANDBOX_IIPS, BACKUP)
    if variant == "A":
        if current != PATCHED_SHA and os.path.isfile(BACKUP):
            shutil.copy2(BACKUP, SANDBOX_IIPS)
        target_sha = sha(SANDBOX_IIPS)
        if target_sha != PATCHED_SHA:
            raise SystemExit("variant A needs patched bytes; current=" + target_sha)
    elif variant == "B":
        shutil.copy2(BASELINE, SANDBOX_IIPS)
        target_sha = sha(SANDBOX_IIPS)
        if target_sha != BASELINE_SHA:
            raise SystemExit("baseline copy failed; current=" + target_sha)
    else:
        raise SystemExit("variant must be A or B")
    state = {
        "variant": variant,
        "sha": target_sha,
        "backup": BACKUP,
        "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(json.dumps(state, indent=2, ensure_ascii=False))


def cmd_restore():
    ensure_safe_paths()
    if os.path.isfile(BACKUP):
        shutil.copy2(BACKUP, SANDBOX_IIPS)
        print("restored sandbox iips.dll:", sha(SANDBOX_IIPS))
    else:
        print("no A/B backup found; sandbox left unchanged")


def analyze_run(variant, run_dir):
    run_dir = os.path.abspath(run_dir)
    out = {
        "variant": variant.upper(),
        "run_dir": run_dir,
        "run_exists": os.path.isdir(run_dir),
        "iips_sha_at_analysis": sha(SANDBOX_IIPS),
        "hostpid": read_hostpid(),
        "iips_pipes_now": list_iips_pipes(),
        "processes_now": process_rows(),
        "files": {},
    }
    if out["run_exists"]:
        for name in ("game_status.json", "game_launch.json", "status.txt",
                     "hostpid_before.txt", "hostpid_after.txt", "identity.json"):
            path = os.path.join(run_dir, name)
            if os.path.isfile(path):
                try:
                    out["files"][name] = open(
                        path, "r", encoding="utf-8", errors="replace").read()
                except Exception as exc:
                    out["files"][name] = "ERROR " + repr(exc)
        logs = glob.glob(os.path.join(run_dir, "tenio_logs", "*.log"))
        out["tenio_log_count"] = len(logs)
        hits = []
        needles = ("connect to policy", "listen to pipe", "hostpid",
                   "failed to conncet pipe", "resourcemanagerii",
                   "iipsres", "loadimage")
        for path in logs:
            try:
                text = open(path, "r", encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for line in text.splitlines():
                if any(n in line.lower() for n in needles):
                    hits.append({"file": os.path.basename(path), "line": line})
        out["tenio_hits"] = hits[-80:]
    report_path = os.path.join(run_dir, "_s2_ab_analysis.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("report:", report_path)
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_observe(minutes):
    end = time.time() + max(1, minutes) * 60
    while time.time() < end:
        row = {
            "t": round(time.time(), 3),
            "iips_sha": sha(SANDBOX_IIPS),
            "hostpid": read_hostpid(),
            "iips_pipes": list_iips_pipes(),
            "processes": process_rows(),
        }
        print(json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(1.0)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1].lower()
    if cmd == "prepare":
        if len(sys.argv) < 3:
            raise SystemExit("prepare requires A or B")
        cmd_prepare(sys.argv[2])
    elif cmd == "restore":
        cmd_restore()
    elif cmd == "analyze":
        if len(sys.argv) < 4:
            raise SystemExit("analyze requires variant and run directory")
        analyze_run(sys.argv[2], sys.argv[3])
    elif cmd == "observe":
        cmd_observe(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
    elif cmd == "status":
        print(json.dumps({
            "current_sha": sha(SANDBOX_IIPS),
            "baseline_sha": sha(BASELINE),
            "backup_exists": os.path.isfile(BACKUP),
            "hostpid": read_hostpid(),
            "iips_pipes": list_iips_pipes(),
        }, indent=2, ensure_ascii=False))
    elif cmd == "cleanup":
        kill_experiment_processes()
        print("cleanup done")
    else:
        raise SystemExit("unknown command: " + cmd)


if __name__ == "__main__":
    main()
