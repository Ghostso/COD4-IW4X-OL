import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
p = Path("E:/CODOL_SANDBOX/RUN001/Ayria/Injector32.exe")
data = p.read_bytes()
print("size", len(data), "sha256-prefix", __import__("hashlib").sha256(data).hexdigest().upper()[:16])
s = re.findall(rb"[\x20-\x7e]{5,}", data)
strings = [x.decode("ascii", "replace") for x in s]
keys = ["Could not create", "create process", "usage", "Usage", "USAGE", "argument", "CommandLine", "command line",
        "Injector", "injector", "exe", "error", "Error", "argv", "Bootstrapper", "LoadLibrary", "target", "Target"]
seen = set()
for t in strings:
    low = t.lower()
    if any(k.lower() in low for k in keys):
        if t not in seen:
            seen.add(t)
            print(repr(t))
print("--- dll imports ---")
for m in re.finditer(rb"[A-Za-z0-9_\-]{3,}\.dll", data):
    print(m.group(0).decode("ascii", "replace"))
