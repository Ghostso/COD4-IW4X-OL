# -*- coding: utf-8 -*-
"""NEXT-010 minimal read-only instrumentation (anchored, idempotent, no behavior change).

usage: python -X utf8 apply_capture_patch.py <copy-dir>
"""
import io
import os
import sys

MARK = "CAPTURE_TARGETS = frozenset"

BLOCK_CAPS = """

# ====================================================================
# NEXT-010 read-only capture instrumentation (copy only; default OFF)
#   switch file : capture-21-5.enabled  (present = record)
#   output      : capture-21-5.meta / capture-21-5.hex (append only)
#   records no keys/credentials; only IV/ciphertext/plaintext + metadata
# ====================================================================
CAPTURE_FLAG = os.path.join(OUTDIR, "capture-21-5.enabled")
CAPTURE_META = os.path.join(OUTDIR, "capture-21-5.meta")
CAPTURE_HEX = os.path.join(OUTDIR, "capture-21-5.hex")
CAPTURE_TARGETS = frozenset([(21, 5), (6, 14)])
_CAPS = {"seq": 0, "cid": None}
_CAPS_LOCK = threading.Lock()


def _cap_on():
    try:
        return os.path.exists(CAPTURE_FLAG)
    except Exception:
        return False


def _cap_begin():
    # Called once at the TOP of every connection. Resets state;
    # allocates a session id ONLY when the switch is on.
    with _CAPS_LOCK:
        _CAPS["cid"] = None
    if not _cap_on():
        return None
    with _CAPS_LOCK:
        _CAPS["seq"] += 1
        cid = "c%04d" % _CAPS["seq"]
        _CAPS["cid"] = cid
    return cid


def _cap_set(cid, addr):
    # Record the session id + peer for this connection (switch-gated).
    if not _cap_on() or not cid:
        return
    with _CAPS_LOCK:
        _CAPS["cid"] = cid
    _cap_meta("SESSION-BEGIN", cid, "NA", 0, 0, 0, 0, True, "peer=%s" % (addr,), "")


def _cap_frame(direction, parsed, raw, service, task, seq, declared):
    # Records a frame. Reads the module-level session id, so it is safe
    # to call from ANY function (no closure / local-variable dependency).
    if not _cap_on():
        return
    cid = _CAPS.get("cid")
    if not cid:
        return
    try:
        if (int(service), int(task)) not in CAPTURE_TARGETS:
            return
    except Exception:
        return
    sha = ""
    if raw:
        try:
            sha = hashlib.sha256(raw).hexdigest()
        except Exception:
            sha = ""
    _cap_meta("FRAME", cid, direction, service, task, seq,
              len(raw) if raw else 0, parsed is not None, "", sha)
    if raw:
        _cap_hex(cid, direction, len(raw), raw)


def _cap_meta(kind, cid, direction, service, task, seq, length, parsed_ok, note, sha):
    if not _cap_on():
        return
    rec = ("%s.%03d" + chr(9) + "%s" + chr(9) + "%s" + chr(9) + "%s"
           + chr(9) + "service=%s" + chr(9) + "task=%s" + chr(9) + "seq=%s"
           + chr(9) + "len=%s" + chr(9) + "parsed_ok=%s" + chr(9)
           + "sha256=%s" + chr(9) + "%s" + chr(10)) % (
        time.strftime("%Y-%m-%dT%H:%M:%S"), int(time.time() * 1000) % 1000,
        kind, cid, direction, service, task, seq, length, parsed_ok, sha, note)
    try:
        with _CAPS_LOCK:
            with open(CAPTURE_META, "a", encoding="utf-8") as f:
                f.write(rec)
                f.flush()
    except Exception:
        pass


def _cap_hex(cid, direction, length, raw):
    line = "> %s %s len=%d" % (cid, direction, length) + chr(10) + raw.hex() + chr(10)
    try:
        with _CAPS_LOCK:
            with open(CAPTURE_HEX, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
    except Exception:
        pass
"""

def _anchor(a):
    return a

WRAP_OLD = "def handle_lobby(conn, addr):" + chr(10)
WRAP_NEW = (
    "def handle_lobby(conn, addr):" + chr(10)
    + "    # NEXT-010: manage module-level capture state for this connection" + chr(10)
    + "    _cap_begin()" + chr(10)
    + "    try:" + chr(10)
    + "        _cap_set(_CAPS.get(\"cid\"), addr)" + chr(10)
    + "        _handle_lobby_impl(conn, addr)" + chr(10)
    + "    finally:" + chr(10)
    + "        with _CAPS_LOCK:" + chr(10)
    + "            _CAPS[\"cid\"] = None" + chr(10)
    + chr(10)
    + chr(10)
    + "def _handle_lobby_impl(conn, addr):" + chr(10)
)

PATCHES = [
    ("OUTDIR = os.path.dirname(os.path.abspath(__file__))" + chr(10),
     "OUTDIR = os.path.dirname(os.path.abspath(__file__))" + chr(10) + BLOCK_CAPS),
    # P2: wrap handle_lobby so the module-level capture state is per-connection
    (WRAP_OLD, WRAP_NEW),
    ("                    ntasks += 1" + chr(10),
     "                    _cap_frame(\"C2S-PLAIN\", r, fr, r.get(\"service\"), r.get(\"task\"), r.get(\"seq\"), r.get(\"declared\"))" + chr(10)
     + "                    ntasks += 1" + chr(10)),
    ("                        conn.sendall(rep)" + chr(10),
     "                        conn.sendall(rep)" + chr(10)
     + "                        _cap_frame(\"S2C-PLAIN\", r, rep, r.get(\"service\"), r.get(\"task\"), out_seq - 1, r.get(\"declared\"))" + chr(10)),
    ("                            conn.sendall(pf)" + chr(10),
     "                            conn.sendall(pf)" + chr(10)
     + "                            _cap_frame(\"S2C-PUSH\", None, pf, r.get(\"service\"), r.get(\"task\"), _pseq, 2)" + chr(10)),
]


def apply(path):
    with io.open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if MARK in src:
        print("already patched: %s" % path)
        return True
    out = src
    for idx, (anchor, repl) in enumerate(PATCHES, 1):
        n = out.count(anchor)
        if n != 1:
            print("ABORT: anchor #%d matched %d times (need exactly 1)" % (idx, n))
            print("   anchor = %r" % (anchor[:90],))
            return False
        out = out.replace(anchor, repl, 1)
    if out.count(MARK) != 1:
        print("ABORT: block count = %d" % out.count(MARK))
        return False
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("patched: %s (delta %+d chars)" % (path, len(out) - len(src)))
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -X utf8 apply_capture_patch.py <copy-dir>")
        sys.exit(2)
    target = os.path.join(sys.argv[1], "lobby_server.py")
    if not os.path.exists(target):
        print("not found: " + target)
        sys.exit(3)
    sys.exit(0 if apply(target) else 4)
