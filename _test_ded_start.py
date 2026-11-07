import os, subprocess, time

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")

env = os.environ.copy()
env["OLMOD_PROCESS_ROLE"] = "dedicated"
env["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
env["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
env["OLMOD_ROOM_OWNER_PORT"] = "28970"
env["OLMOD_CONSOLE_LOG"] = "1"
env["OLMOD_CLAIM_LOBBY"] = "1"

# Prepare powershell command matching Launch_OLMod.bat
ps_cmd = f"$ErrorActionPreference='Stop'; $s=[System.Diagnostics.ProcessStartInfo]::new(); $s.FileName='{injector}'; $s.Arguments='\"{target}\" -qa'; $s.WorkingDirectory='{game_dir}'; $s.UseShellExecute=$false; $p=[System.Diagnostics.Process]::Start($s);"

print("Starting Dedicated Server via PowerShell ProcessStartInfo...")
p = subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ps_cmd], cwd=game_dir, env=env)
p.wait()

print("Launched injector, waiting 8 seconds for dedicated server startup...")
time.sleep(8)

# Check processes
res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
pids = [r for r in res.stdout.strip().splitlines() if 'codoMP' in r]
print("Running codoMP processes:", pids)

# Check listening ports (28960, 28961, 28970)
net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
for line in net.stdout.splitlines():
    if any(port in line for port in [":28960", ":28961", ":28970"]):
        print("  ", line)

# Check logs
for name in ["CodolGameServer.log", "CODOLLauncher-dedicated.log"]:
    p_log = os.path.join(game_dir, "Ayria", "Logs", name)
    if os.path.exists(p_log):
        print(f"\n=== {name} ===")
        print(open(p_log, "r", encoding="utf-8", errors="replace").read())
