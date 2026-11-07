"""T-2.5 Stage 1: T-1 regression artifact check + transport lifecycle test run.

Read-only w.r.t. CODOL: runs an offline prebuilt gtest binary and compares the
three T-1 test-artifact hashes against the T-2 acceptance manifest. Port state is
sampled before and after to prove the run leaves no socket behind.
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
BIN = Path(r"F:\桌面\ol\ol-mod-olfinal\build\bin\release")
TZ = timezone(timedelta(hours=8))
PORTS = (28960, 28961, 28962, 28970)

EXPECTED = {
    "ol_transport_lifecycle_tests.exe": ("FD503FAAC0AC61F8605F863BEB8161481B69A6D42C0C2D472CD19A7232307EF0", 3830272),
    "ol_game_server_tests.exe": ("706CAE920707DA8976F047E14878BB3CCC546915C566B9BAFDF66DE68D09CCEB", 7482368),
    "ol_lua_runtime_tests.exe": ("9205E4BBE39EB9F5C5B24D483ED2245E8C93B0168385312D27560743D7DEC151", 4534784),
}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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
            rows.append({"local": local, "state": parts[3], "ownerPid": parts[-1]})
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    document: dict = {"collectedAt": iso(time.time())}

    artifacts = {}
    for name, (expected, size) in EXPECTED.items():
        path = BIN / name
        row = {"path": str(path), "exists": path.is_file(),
               "expectedSha256": expected, "expectedSize": size}
        if row["exists"]:
            row["sha256"] = sha256(path)
            row["size"] = path.stat().st_size
            row["mtime"] = iso(path.stat().st_mtime)
            row["unchanged"] = (row["sha256"] == expected and row["size"] == size)
        document.setdefault("artifacts", {})[name] = row
    document["artifactsAllUnchanged"] = all(v.get("unchanged") for v in document["artifacts"].values())

    exe = BIN / "ol_transport_lifecycle_tests.exe"
    document["portsBefore"] = port_rows()
    started = time.time()
    proc = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False, timeout=300)
    ended = time.time()
    document["portsAfter"] = port_rows()
    document["transportLifecycle"] = {
        "argv": [str(exe)],
        "startedAt": iso(started), "endedAt": iso(ended), "durationS": round(ended - started, 3),
        "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
    }
    (EVIDENCE / "raw_tests.T1.transport.log").write_text(
        "ARGV: " + str([str(exe)]) + "\nSTART: " + iso(started) + "\nEND: " + iso(ended) +
        "\nEXIT: " + str(proc.returncode) + "\n--- STDOUT ---\n" + proc.stdout +
        "\n--- STDERR ---\n" + proc.stderr + "\n", encoding="utf-8")
    (EVIDENCE / "t1_regression_evidence.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    print("artifactsAllUnchanged:", document["artifactsAllUnchanged"])
    for name, row in document["artifacts"].items():
        print(" ", name, "unchanged=" + str(row.get("unchanged")), "size=" + str(row.get("size")))
    print("transport exit:", proc.returncode)
    print("portsBefore:", document["portsBefore"])
    print("portsAfter:", document["portsAfter"])
    tail = [l for l in proc.stdout.splitlines() if l.strip()][-8:]
    print("stdout tail:")
    for line in tail:
        print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
