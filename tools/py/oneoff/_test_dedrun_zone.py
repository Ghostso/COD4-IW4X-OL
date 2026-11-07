import subprocess, time, os

server_bin_dir = r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin"
exe = os.path.join(server_bin_dir, "codol_dedrun_next.exe")
game_root = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
home_dir = os.path.join(server_bin_dir, "home")
zone_path = os.path.join(game_root, "main")

cmd = [
    exe,
    "+set", "dedicated", "2",
    "+set", "fs_basepath", game_root,
    "+set", "fs_homepath", home_dir,
    "+set", "codol_zonePath", zone_path,
    "+set", "net_port", "28960",
    "+set", "developer", "1",
    "+set", "logfile", "2",
    "+set", "g_gametype", "coop",
    "+set", "codol_admissionRequired", "0",
    "+map", "mp_firingrange"
]

print("Executing test run of codol_dedrun_next.exe with codol_zonePath...")
p = subprocess.Popen(cmd, cwd=server_bin_dir)

time.sleep(5)
print("Checking process status after 5 seconds...")
is_alive = p.poll() is None
print(f"Server process alive: {is_alive} (PID={p.pid})")

log_path = os.path.join(home_dir, "main", "qconsole.log")
if os.path.exists(log_path):
    lines = open(log_path, "r", encoding="utf-8", errors="replace").readlines()
    print("--- qconsole.log tail 30 lines ---")
    for l in lines[-30:]:
        print(" ", l, end="")

if is_alive:
    print("\nTerminating test server...")
    p.terminate()
