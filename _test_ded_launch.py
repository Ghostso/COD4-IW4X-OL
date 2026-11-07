import subprocess, time, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_dedicated_server.exe")

env = os.environ.copy()
env["OLMOD_PROCESS_ROLE"] = "dedicated"
env["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
env["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
env["OLMOD_ROOM_OWNER_PORT"] = "28970"
env["OLMOD_CONSOLE_LOG"] = "1"
env["OLMOD_CLAIM_LOBBY"] = "1"

# Clean old log
log_path = os.path.join(game_dir, "Ayria", "Logs", "CodolGameServer.log")
if os.path.exists(log_path):
    try: os.remove(log_path)
    except: pass

ps_cmd = f"$ErrorActionPreference='Stop'; $s=[System.Diagnostics.ProcessStartInfo]::new(); $s.FileName='{injector}'; $s.Arguments='\"{target}\"'; $s.WorkingDirectory='{game_dir}'; $s.UseShellExecute=$true; [System.Diagnostics.Process]::Start($s);"

print("Launching Native Dedicated Server (codoMP_dedicated_server.exe)...")
subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ps_cmd], cwd=game_dir, env=env)

print("Waiting 8 seconds for startup, initialization, and port binding...")
time.sleep(8)

# Check processes
res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_dedicated_server.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
pids = [r for r in res.stdout.strip().splitlines() if 'dedicated' in r or 'codoMP' in r]
print("Running dedicated server process:", pids)

# Check listening ports (28960, 28961, 28970)
net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
print("Active listening sockets:")
for line in net.stdout.splitlines():
    if any(port in line for port in [":28960", ":28961", ":28970"]):
        print("  ", line.strip())

# Check CodolGameServer.log
if os.path.exists(log_path):
    print("\n=== CodolGameServer.log ===")
    print(open(log_path, "r", encoding="utf-8", errors="replace").read())
else:
    print("\nCodolGameServer.log not found yet!")
