with open("REF_LOBBY_KIT/lobby_srv.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

import re
line = lines[294]
m = line.split(":", 1)[1]
hex_chars = "".join(c for c in m if c in "0123456789abcdefABCDEF")
if len(hex_chars) % 2 != 0: hex_chars = hex_chars[:-1]
raw = bytes.fromhex(hex_chars)

# Split by pipe '|' which is common in CODOL telemetry
print("Raw length:", len(raw))
parts = raw.split(b"|")
for idx, p in enumerate(parts):
    printable = "".join(chr(b) if 32 <= b < 127 else f"\\x{b:02x}" for b in p)
    print(f"[{idx}] {printable}")
