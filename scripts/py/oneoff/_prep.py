import os, subprocess

# 1. Kill any existing game or combat server processes
for proc in ["codoMP_client_shipRetail.exe", "CODOLCombatServer.exe"]:
    subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True)

# 2. Rename battle server flag so lobby does NOT start C# server
flag = r"REF_LOBBY_KIT\firingrange-battle.enabled"
if os.path.exists(flag):
    bak = flag + ".bak"
    if os.path.exists(bak):
        os.remove(bak)
    os.rename(flag, bak)
    print("Disabled firingrange-battle.enabled!")
else:
    print("Battle flag already disabled.")

# 3. Clean old logs
for p in [
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Logs\CodolGameServer.log",
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Logs\CodolGameServer.log"
]:
    if os.path.exists(p):
        os.remove(p)
        print(f"Removed {p}")

print("Preparation complete!")
