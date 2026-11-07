with open("REF_LOBBY_KIT/lobby_srv.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "declared=779" in l or "payload(776)" in l:
        print(f"--- Found at line {i} ---")
        for j in range(max(0, i-2), min(len(lines), i+6)):
            print(lines[j].rstrip())
        # The next line contains the payload
        pl_line = lines[i+1]
        m = pl_line.split(":", 1)
        if len(m) > 1:
            raw_hex = m[1].strip()
            raw_bytes = bytes.fromhex(raw_hex.replace(" ", ""))
            print("\nDECODED STRING:")
            print(raw_bytes.decode("ascii", errors="replace"))
