import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
log_path = os.path.join(game_dir, "Ayria", "Logs", "CodolGameServer.log")
if os.path.exists(log_path):
    os.remove(log_path)

subprocess.run(["taskkill", "/F", "/IM", "codoMP_client_shipRetail.exe"], capture_output=True)

bat_path = os.path.join(game_dir, "Launch_OLMod.bat")
print("Launching Launch_OLMod.bat...")
subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=game_dir)

time.sleep(6)

if os.path.exists(log_path):
    print("=== CodolGameServer.log ===")
    print(open(log_path, "r", encoding="utf-8", errors="replace").read())
else:
    print("CodolGameServer.log not created.")

res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
print("Processes:", [r for r in res.stdout.strip().splitlines() if 'codoMP' in r])
