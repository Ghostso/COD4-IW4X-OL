import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_num_getter.log")

buf = io.StringIO()
try:
    sys.path.insert(0, os.path.join(HERE, ".."))
    r = __import__("_recv_gate_disasm")
    img = open(r.IMG, "rb").read()
    lines = r.disasm(img, 0xAD4630, 0xAD4A70)
    r.OUT = HERE
    r.write_report("ad4600_4700.txt", lines)
    buf.write("lines=%d\n" % len(lines))
except Exception:
    buf.write(traceback.format_exc())
open(LOG, "w", encoding="utf-8").write(buf.getvalue())
print("done")
