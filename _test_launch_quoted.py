import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")

# Quote target as [char]34 in Launch_OLMod.bat
quoted_target = f'"{target}"'
print("Running:", injector, quoted_target)

# Clean old log
log_path = os.path.join(game_dir, "Ayria", "Logs", "CodolGameServer.log")
if os.path.exists(log_path):
    os.remove(log_path)

p = subprocess.Popen([injector, quoted_target], cwd=game_dir)
print("Waiting 6 seconds for injection, TP3 unpack, and retry loop...")
time.sleep(6)

if os.path.exists(log_path):
    print("\n=== CodolGameServer.log ===")
    print(open(log_path, "r", encoding="utf-8", errors="replace").read())
else:
    print("CodolGameServer.log not created yet!")

boot_log = os.path.join(game_dir, "Ayria", "Logs", "Bootstrapper32.log")
if os.path.exists(boot_log):
    print("\n=== Bootstrapper32.log ===")
    print(open(boot_log, "r", encoding="utf-8", errors="replace").read())

# Check running processes
res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
print("\nRunning processes:", [r for r in res.stdout.strip().splitlines() if 'codoMP' in r])
