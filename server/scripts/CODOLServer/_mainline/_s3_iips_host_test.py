"""S3: isolate the IIPS host layer.

Launches IIPSHostApp.exe /mode iipslaunch, then checks whether it
  (a) stays alive,
  (b) writes its own PID into IIPS\\HostPid,
  (c) creates a named pipe.

Run elevated. Does not touch the network stack.
"""
import ctypes
import glob
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"


def read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def pipes():
    try:
        names = os.listdir("\\\\.\\pipe\\")
    except Exception as exc:
        return [], "ERR %s" % exc
    pat = re.compile(r"iips|tenio|tcls|tenio|host", re.I)
    return [n for n in names if pat.search(n)], None


def run(tree, seconds):
    iips_dir = os.path.join(tree, "IIPS")
    host = os.path.join(iips_dir, "IIPSHostApp.exe")
    hostpid = os.path.join(iips_dir, "HostPid")

    print("tree      = %s" % tree)
    print("host exe  = %s exists=%s" % (host, os.path.isfile(host)))
    before = read(hostpid)
    print("HostPid before = %r (%s)"
          % (before, "missing" if before is None else "%d B" % len(before)))
    p0, err = pipes()
    print("iips pipes before = %d %s" % (len(p0), err or ""))
    if not os.path.isfile(host):
        return 1

    proc = subprocess.Popen([host, "/mode", "iipslaunch"], cwd=iips_dir)
    print("launched pid=%d" % proc.pid)
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        time.sleep(3)
        cur = read(hostpid)
        pl, _ = pipes()
        if cur != last:
            print("  t=%.1fs HostPid=%r pipes=%d"
                  % (time.time() - (deadline - seconds), cur, len(pl)))
            last = cur
        if cur and cur.strip().isdigit() and int(cur.strip()) == proc.pid:
            print("  -> host wrote its OWN pid")
        if proc.poll() is not None:
            print("  host exited rc=%s at %.1fs"
                  % (proc.returncode, time.time() - (deadline - seconds)))
            break

    after = read(hostpid)
    pl, _ = pipes()
    alive = proc.poll() is None
    print()
    print("RESULT tree=%s" % tree)
    print("  host alive      = %s" % alive)
    print("  HostPid after   = %r" % after)
    print("  HostPid written = %s"
          % (after is not None and after != before and len(after or b"") > 0))
    print("  iips pipes      = %d %s" % (len(pl), pl[:8]))
    if alive:
        proc.terminate()
    return 0


def main():
    tree = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "COD OL")
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    return run(tree, seconds)


if __name__ == "__main__":
    sys.exit(main())
