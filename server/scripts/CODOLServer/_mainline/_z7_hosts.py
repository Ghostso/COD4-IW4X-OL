"""Manage the two hosts entries the working document requires.

Authorization (2026-10-02, explicit): "允许使用覆盖还原的方法修改" --
overwrite WITH a restorable snapshot.  So every run:
  1. writes a timestamped backup next to the real file
  2. records the exact original bytes in a sidecar
  3. appends ONLY the two required lines, never touching anything else
and `restore` puts the original bytes back verbatim.

The document is explicit that hijacking down.qq.com / intldlgs.qq.com breaks
ACE/TP3 (they must reach the real servers for config and DLLs), so we
deliberately do NOT redirect those.
"""
import ctypes
import os
import shutil
import sys
import time

HOSTS = r"C:\Windows\System32\drivers\etc\hosts"
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_hosts_snap")

# exactly what the working document specifies -- nothing else
WANT = [
    ("127.0.0.1", "formal-zone-auth.codol.qq.com"),
    ("127.0.0.2", "formal-zone-lsg.codol.qq.com"),
]

# must never be redirected (would cut ACE/TP3 off from the real servers)
FORBIDDEN = ["down.qq.com", "intldlgs.qq.com"]


def read_text(p):
    with open(p, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return raw, raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw, raw.decode("latin-1", "replace")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def snapshot():
    os.makedirs(SNAP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    raw, _ = read_text(HOSTS)
    bak = os.path.join(SNAP_DIR, "hosts.%s.bak" % ts)
    with open(bak, "wb") as f:
        f.write(raw)
    with open(os.path.join(SNAP_DIR, "hosts.original"), "wb") as f:
        f.write(raw)
    print("backup ->", bak)
    print("pristine copy -> %s (%d bytes)"
          % (os.path.join(SNAP_DIR, "hosts.original"), len(raw)))
    return raw


def apply():
    raw, text = read_text(HOSTS)
    print("=== current hosts (non-comment) ===")
    for l in text.splitlines():
        s = l.strip()
        if s and not s.startswith("#"):
            print("   ", l)
    for bad in FORBIDDEN:
        if any(bad in l and not l.strip().startswith("#")
               for l in text.splitlines()):
            raise SystemExit("REFUSING: hosts already hijacks %s" % bad)

    snapshot()
    for _, host in WANT:
        if any(host in l and not l.strip().startswith("#")
               for l in text.splitlines()):
            raise SystemExit("REFUSING: %s already present -- check it first"
                             % host)

    add = "\n# --- CODOL local lobby (restorable; see _z7_hosts.py) ---\n"
    for ip, host in WANT:
        add += "%s\t%s\n" % (ip, host)
    with open(HOSTS, "a", encoding="utf-8", newline="") as f:
        f.write(add)
    print("=== appended ===")
    print(add)
    _, now = read_text(HOSTS)
    print("=== result (non-comment) ===")
    for l in now.splitlines():
        s = l.strip()
        if s and not s.startswith("#"):
            print("   ", l)


def restore():
    src = os.path.join(SNAP_DIR, "hosts.original")
    if not os.path.exists(src):
        raise SystemExit("no pristine copy at %s" % src)
    if not is_admin():
        print("WARNING: not elevated; write may fail")
    shutil.copy2(src, HOSTS)
    _, now = read_text(HOSTS)
    print("restored. non-comment lines now:")
    n = 0
    for l in now.splitlines():
        s = l.strip()
        if s and not s.startswith("#"):
            print("   ", l)
            n += 1
    print("   (%d non-comment lines)" % n)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        _, t = read_text(HOSTS)
        for l in t.splitlines():
            s = l.strip()
            if s and not s.startswith("#"):
                print(l)
    elif cmd == "apply":
        apply()
    elif cmd == "restore":
        restore()
    else:
        print("usage: _z7_hosts.py show|apply|restore")
