"""S3: does IIPSHostApp start its pipe once the policy server answers?

Launches IIPSHostApp.exe /mode iipslaunch, watches HostPid + named pipes,
and (optionally) serves a UDP policy endpoint on 127.0.0.1:8000 so we can
see which of the two preconditions actually gates pipe creation.

Run elevated. Never touches netsh / routes / DNS / adapters.
"""
import argparse
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"


def read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def iips_pipes():
    try:
        names = os.listdir("\\\\.\\pipe\\")
    except Exception as exc:
        return [], "ERR %s" % exc
    pat = re.compile(r"iips|tenio|tcls|policy", re.I)
    return [n for n in names if pat.search(n)], None


class UdpLog(object):
    def __init__(self, port, out):
        self.port = port
        self.out = out
        self.sock = None
        self.stop = threading.Event()
        self.pkts = []

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(1.0)
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self.stop.is_set():
            try:
                data, addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            rec = {"t": round(time.time(), 3), "from": addr[0],
                   "port": addr[1], "len": len(data),
                   "hex": data[:96].hex()}
            self.pkts.append(rec)
            with open(self.out, "a", encoding="utf-8") as fh:
                fh.write(json_line(rec))

    def stop_it(self):
        self.stop.set()
        if self.sock:
            self.sock.close()


def json_line(obj):
    import json
    return json.dumps(obj, ensure_ascii=False) + "\n"


def run(tree, seconds, listen_port, out_dir):
    iips_dir = os.path.join(tree, "IIPS")
    host = os.path.join(iips_dir, "IIPSHostApp.exe")
    hostpid = os.path.join(iips_dir, "HostPid")
    os.makedirs(out_dir, exist_ok=True)
    udp_log = os.path.join(out_dir, "policy_udp.jsonl")

    print("tree = %s" % tree)
    print("host = %s exists=%s" % (host, os.path.isfile(host)))
    before = read(hostpid)
    print("HostPid before = %r" % before)
    if not os.path.isfile(host):
        return 1

    udp = None
    if listen_port:
        udp = UdpLog(listen_port, udp_log)
        try:
            udp.start()
            print("UDP listener on 0.0.0.0:%d" % listen_port)
        except OSError as exc:
            print("UDP bind failed: %s" % exc)
            udp = None

    p0, _ = iips_pipes()
    print("iips pipes before = %d %s" % (len(p0), p0[:5]))

    proc = subprocess.Popen([host, "/mode", "iipslaunch"], cwd=iips_dir)
    print("launched pid=%d" % proc.pid)

    t0 = time.time()
    seen = set()
    wrote = False
    while time.time() - t0 < seconds:
        time.sleep(2)
        el = time.time() - t0
        cur = read(hostpid)
        pl, _ = iips_pipes()
        for n in pl:
            if n not in seen:
                seen.add(n)
                print("  t=%.1fs NEW PIPE %s" % (el, n))
        if cur and cur != before and cur.strip():
            wrote = True
            print("  t=%.1fs HostPid CHANGED -> %r" % (el, cur))
        if proc.poll() is not None:
            print("  host exited rc=%s t=%.1fs" % (proc.returncode, el))
            break

    print()
    print("RESULT")
    print("  host alive        = %s" % (proc.poll() is None))
    print("  HostPid written   = %s (%r)" % (wrote, read(hostpid)))
    print("  new iips pipes    = %d %s" % (len(seen), sorted(seen)[:8]))
    if udp:
        print("  UDP policy pkts   = %d" % len(udp.pkts))
        for r in udp.pkts[:5]:
            print("     %s" % r)
        udp.stop_it()
    if proc.poll() is None:
        proc.terminate()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=os.path.join(ROOT, "COD OL"))
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--listen-port", type=int, default=0,
                    help="0 = no UDP listener")
    ap.add_argument("--out", default=os.path.join(ROOT, "CODOLServer",
                                                  "_s3_policy_probe"))
    args = ap.parse_args()
    return run(args.tree, args.seconds, args.listen_port, args.out)


if __name__ == "__main__":
    sys.exit(main())
