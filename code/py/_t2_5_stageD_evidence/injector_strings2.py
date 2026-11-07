import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

def strings(data, minlen=4):
    out = set()
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data):
        out.add(m.group(0).decode("ascii", "replace"))
    for m in re.finditer((rb"(?:[\x20-\x7e]\x00){%d,}" % minlen), data):
        out.add(m.group(0).decode("utf-16-le", "replace"))
    return sorted(out)

for name in ("Injector32.exe", "Bootstrapper32.dll"):
    p = Path("E:/CODOL_SANDBOX/RUN001/Ayria") / name
    print("=" * 20, name, p.stat().st_size)
    ss = strings(p.read_bytes())
    print("total strings:", len(ss))
    keys = ["create", "process", "error", "Error", "fail", "Fail", "exe", "path", "Path",
            "target", "Target", "command", "Command", "argv", "usage", "Usage",
            "OLMOD", "boot", "Boot", "inject", "Inject", "dll", "DLL", "CODOL", "Ayria"]
    hits = [t for t in ss if any(k in t for k in keys)]
    for t in hits[:120]:
        print(repr(t))
