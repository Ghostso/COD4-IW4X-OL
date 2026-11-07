with open("REF_LOBBY_KIT/lobby_srv.log", "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

import re
matches = re.findall(r"payload\(\d+\):\s+([0-9a-fA-F ]{30,})", text)
print(f"Total hex payloads found: {len(matches)}")
for m in matches[-10:]:
    raw = bytes.fromhex(m.replace(" ", ""))
    txt = "".join(chr(c) if 32 <= c < 127 else "." for c in raw)
    print(f"Len {len(raw)}: {txt[:120]}")
