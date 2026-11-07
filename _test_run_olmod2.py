import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")

print(f"Target: {target}")
print(f"Injector: {injector}")
assert os.path.isfile(target), "Target missing!"
assert os.path.isfile(injector), "Injector missing!"

cmd = [injector, target, "-qa"]
p = subprocess.Popen(cmd, cwd=game_dir)
print("Injector started, waiting 8 seconds for TP3 unpack & retry loop...")
time.sleep(8)

for log_name in ["CodolGameServer.log", "Bootstrapper32.log", "Localnetworking.log"]:
    p_log = os.path.join(game_dir, "Ayria", "Logs", log_name)
    if os.path.exists(p_log):
        print(f"\n--- {log_name} ---")
        print(open(p_log, "r", encoding="utf-8", errors="replace").read())
    else:
        print(f"\n{log_name}: Not found")
