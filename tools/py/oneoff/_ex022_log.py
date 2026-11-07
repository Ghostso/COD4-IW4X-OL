import time
from pathlib import Path

root = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
logs = root / "工具" / "logs"
stamp = time.strftime("%Y%m%d-%H%M%S")
out = logs / f"ex022_bootstrap_exit_{stamp}.log"

with out.open("w", encoding="utf-8") as f:
    f.write("CODOL_EX022_BOOTSTRAP_EXIT_LOG\n")
    f.write("time=" + time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n")
    f.write("experiment=EX-022\n")
    f.write("observed=VM_BOUNDARY_REACHED\n")
    f.write("vm_boundary_rva=Base+0x1AA13B0\n")
    f.write("first_boundary_retaddr=0x77C131A6\n")
    f.write("ntcreatethreadex=YES\n")
    f.write("tcls_api_trace=NOT_CAPTURED\n")
    f.write("first_exception=KERNEL32!IsBadReadPtr+0x5a\n")
    f.write("root_cause_classification=UNRESOLVED\n")
print(out)
