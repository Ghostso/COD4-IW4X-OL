import io
import traceback

SCRIPT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_recv_gate_disasm.py"
LOG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_recv_gate\_run.log"

buf = io.StringIO()
src = open(SCRIPT, encoding="utf-8").read()
try:
    exec(compile(src, SCRIPT, "exec"), {"__name__": "__main__"})
except SystemExit as e:
    buf.write("SystemExit %r\n" % e)
except Exception:
    buf.write(traceback.format_exc())
open(LOG, "w", encoding="utf-8").write(buf.getvalue())
print("log written")
