import os, subprocess, time

game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")

ps_cmd = f"$ErrorActionPreference='Stop'; $s=[System.Diagnostics.ProcessStartInfo]::new(); $s.FileName='{injector}'; $s.Arguments='\"{target}\"'; $s.WorkingDirectory='{game_dir}'; $s.UseShellExecute=$true; $p=[System.Diagnostics.Process]::Start($s); $p.WaitForExit(); exit $p.ExitCode"

print("Running PowerShell ProcessStartInfo launcher...")
res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd], cwd=game_dir)
print("Launcher exit code:", res.returncode)

time.sleep(3)
procs = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
print("Processes:", [r for r in procs.stdout.strip().splitlines() if 'codoMP' in r])
