import os

root = os.path.dirname(os.path.abspath("run_combat_pipeline.py"))

for fname in ["test_full_wire_inmatch.py", "test_live_wire_combat.py"]:
    fpath = os.path.join(root, fname)
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if "nat_probe[27:29] = struct.pack" in line:
            new_lines.append("    nat_probe[27:29] = struct.pack(\"<H\", server_addr[1])\n")
        elif "sys.path.insert(0," in line:
            new_lines.append("sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REF_LOBBY_KIT'))\n")
        elif "SERVER_EXE =" in line:
            new_lines.append("SERVER_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'build', 'bin', 'CODOLCombatServer.exe')\n")
        elif "CONFIG_FILE =" in line:
            new_lines.append("CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'config', 'firingrange_live.cfg')\n")
        elif "WORKDIR =" in line:
            new_lines.append("WORKDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1')\n")
        else:
            new_lines.append(line)
            
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Fixed", fname)
