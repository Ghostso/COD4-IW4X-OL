import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = "codoMP_client_shipRetail.exe"

print("Starting Injector32 in", game_dir)
cmd = [injector, target, "-qa"]
p = subprocess.Popen(cmd, cwd=game_dir)
print("Injector process started, waiting 6 seconds for unpack & retry loop...")
time.sleep(6)

log_path = os.path.join(game_dir, "Ayria", "Logs", "CodolGameServer.log")
if os.path.exists(log_path):
    print("--- CodolGameServer.log ---")
    print(open(log_path, "r", encoding="utf-8", errors="replace").read())
else:
    print("CodolGameServer.log not found yet!")
