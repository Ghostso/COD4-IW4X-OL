"""Run a child command and persist its stdout/stderr to a file, because this
shell trims stdout for short-lived processes.  Usage:
    python _z7_wrap.py <logfile> <cmd> [args...]
"""
import subprocess
import sys

log = sys.argv[1]
cmd = sys.argv[2:]
p = subprocess.run(cmd, capture_output=True, timeout=900)
with open(log, "wb") as f:
    f.write(b"rc=" + str(p.returncode).encode() + b"\n")
    f.write(b"===== STDOUT =====\n" + (p.stdout or b"") + b"\n")
    f.write(b"===== STDERR =====\n" + (p.stderr or b"") + b"\n")
print("wrote %s rc=%d out=%d err=%d" % (log, p.returncode,
                                        len(p.stdout or b""), len(p.stderr or b"")))
