#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connectionless (out-of-band) probe for the native CoDOL match server.

Sends the three Quake OOB requests the C1/lobby control plane relies on
(`getinfo`, `getstatus`, and optionally `rcon <pw> status`) to the game
server from an *IPv4* socket and prints the reply or a timeout. This is the
client-free reproduction for the "server executes the request but the reply
never arrives" symptom: before the 2026-09-22 fix, the native server swallowed
every OOB reply to an address that had no bdDTLS association (see
docs/CODOL_OOB_REPLY_20260922.md).

A bare `getinfo`/`getstatus` is harmless and does not disturb a connected
player -- it only asks the server to describe itself. `rcon status` requires
the rcon password and merely reads state. NONE of these touch snapshot/actor
code. Still: only run this against a live server when the parent session has
told you the server may be probed.

Usage:
    python tools/codol_oob_probe.py                 # getinfo + getstatus, 127.0.0.1:17733
    python tools/codol_oob_probe.py --rcon PASSWORD # also rcon "status"
    python tools/codol_oob_probe.py --host 127.0.0.1 --port 17733 --timeout 2.5
"""
import argparse
import socket
import sys

OOB = b"\xff\xff\xff\xff"


def probe(sock, addr, payload, timeout):
    sock.settimeout(timeout)
    sock.sendto(OOB + payload, addr)
    try:
        data, _ = sock.recvfrom(65535)
        return data
    except socket.timeout:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=17733)
    ap.add_argument("--timeout", type=float, default=2.5)
    ap.add_argument("--rcon", metavar="PASSWORD",
                    help="also send rcon \"<PASSWORD>\" status")
    args = ap.parse_args()

    addr = (args.host, args.port)
    # Force IPv4 so the reply must come back on the v4 path (mirrors C1/lobby).
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    print("probing %s:%d from %s (IPv4)\n" % (args.host, args.port, sock.getsockname()))

    requests = [("getinfo", b"getinfo xxx"),
                ("getstatus", b"getstatus xxx")]
    if args.rcon:
        requests.append(("rcon status",
                         b'rcon "%s" status' % args.rcon.encode("latin1")))

    any_reply = False
    for name, payload in requests:
        reply = probe(sock, addr, payload, args.timeout)
        if reply is None:
            print("[%-11s] TIMEOUT (%.1fs) -- no reply reached this socket" %
                  (name, args.timeout))
        else:
            any_reply = True
            head = reply[:4] == OOB and reply[4:].split(b"\n", 1)[0] or reply[:32]
            print("[%-11s] %d bytes, head=%r" % (name, len(reply), head))
    sock.close()
    return 0 if any_reply else 1


if __name__ == "__main__":
    sys.exit(main())
