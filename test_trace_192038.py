import sys, os, base64

with open("REF_LOBBY_KIT/lobby_srv.log", "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Search for the line at 19:20:38
lines = text.splitlines()
for i, l in enumerate(lines):
    if "[19:20:38]" in l and "declared=419" in l:
        print(f"Line {i}: {l}")
        pl_line = lines[i+1]
        m = pl_line.split(":", 1)[1]
        hex_chars = "".join(c for c in m if c in "0123456789abcdefABCDEF")
        if len(hex_chars) % 2 != 0: hex_chars = hex_chars[:-1]
        raw = bytes.fromhex(hex_chars)
        for part in raw.split(b"|"):
            p_str = "".join(chr(b) if 32 <= b < 127 else " " for b in part).strip()
            if len(p_str) > 20 and not " " in p_str:
                try:
                    dec = base64.b64decode(p_str).decode("utf-8", errors="replace")
                    print("  [DECODED AS3 TRACE]:", dec)
                except Exception:
                    print(" ", p_str)
            else:
                print(" ", p_str)
