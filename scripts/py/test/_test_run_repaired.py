import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
log_dir = os.path.join(game_dir, "Ayria", "Logs")
for f in ["CodolGameServer.log", "Bootstrapper32.log", "Localnetworking.log"]:
    p = os.path.join(log_dir, f)
    if os.path.exists(p):
        try: os.remove(p)
        except: pass

subprocess.run(["taskkill", "/F", "/IM", "codoMP_client_shipRetail.exe"], capture_output=True)

bat = os.path.join(game_dir, "Launch_OLMod.bat")
print("Launching Launch_OLMod.bat...")
subprocess.Popen(["cmd.exe", "/c", bat], cwd=game_dir)

time.sleep(6)

for f in ["Bootstrapper32.log", "Localnetworking.log", "CodolGameServer.log"]:
    p = os.path.join(log_dir, f)
    if os.path.exists(p):
        print(f"\n=== {f} ===")
        print(open(p, "r", encoding="utf-8", errors="replace").read())
    else:
        print(f"\n{f}: Not created")
