with open("REF_LOBBY_KIT/lobby_srv.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "UIException" in l:
        print(f"Line {i}: {l.strip()}")
        # print next line too
        if i + 1 < len(lines):
            print(f"Next: {lines[i+1].strip()}")
