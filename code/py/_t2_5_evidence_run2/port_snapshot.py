"""T-2.5 Stage 1 read-only port snapshot.

Records, for each project port: any OS-reported owner, and whether a transient
bind succeeds. SO_REUSEADDR is deliberately NOT set, so a successful bind is
meaningful evidence that nothing holds the port.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
PORTS = (28960, 28961, 28962, 28970)
ADDRESSES = ("0.0.0.0", "127.0.0.1")


def netstat_rows():
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        proto = parts[0].upper()
        if proto not in ("UDP", "TCP"):
            continue
        local = parts[1]
        if ":" not in local:
            continue
        port_text = local.rsplit(":", 1)[1]
        if not port_text.isdigit() or int(port_text) not in PORTS:
            continue
        rows.append({
            "protocol": proto,
            "local": local,
            "port": int(port_text),
            "state": parts[3] if proto == "TCP" else "UDP",
            "owner_pid": parts[-1],
        })
    return rows


def try_bind(address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    result = {"address": address, "port": port}
    try:
        sock.bind((address, port))
        result.update(bound=True, error=None, errno=None, winerror=None)
    except OSError as error:
        result.update(bound=False, error=error.strerror, errno=error.errno,
                      winerror=getattr(error, "winerror", None))
    finally:
        sock.close()
    return result


def main() -> int:
    document = {
        "stage": "1 (read-only precheck)",
        "ports": list(PORTS),
        "os_endpoints": netstat_rows(),
        "transient_bind": [try_bind(address, port) for port in PORTS for address in ADDRESSES],
        "note": "SO_REUSEADDR is not set; each probe binds and closes immediately.",
    }
    (EVIDENCE / "port_snapshot.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("os_endpoints=" + str(len(document["os_endpoints"])))
    for row in document["os_endpoints"]:
        print("  " + json.dumps(row, ensure_ascii=False))
    for row in document["transient_bind"]:
        print("  bind " + row["address"] + ":" + str(row["port"]) +
              " -> bound=" + str(row["bound"]) + " winerror=" + str(row["winerror"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
