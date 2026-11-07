import subprocess, sys, time
from pathlib import Path

root = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
logs = root / "工具" / "logs"
stamp = time.strftime("%Y%m%d-%H%M%S")
out = logs / f"exe_full_{stamp}.log"

items = [
    "python _exe_full_pe.py",
    "python _exe_full_tls.py",
    "python _ex021_module_scan.py",
]

with out.open("w", encoding="utf-8") as f:
    f.write("CODOL_EXE_FULL_LOG\n")
    for cmd in items:
        f.write("\n===== " + cmd + " =====\n")
        try:
            res = subprocess.run(cmd.split(), cwd=str(root), capture_output=True, text=True, timeout=90)
            f.write(res.stdout)
            if res.stderr:
                f.write("STDERR\n" + res.stderr)
        except Exception as e:
            f.write("ERROR " + str(e) + "\n")
print(out)
