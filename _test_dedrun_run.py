import subprocess, time, os

server_bin_dir = r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin"
exe = os.path.join(server_bin_dir, "codol_dedrun_next.exe")
game_root = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
home_dir = os.path.join(server_bin_dir, "home")

cmd = [
    exe,
    "+set", "dedicated", "2",
    "+set", "fs_basepath", game_root,
    "+set", "fs_homepath", home_dir,
    "+set", "net_port", "28960",
    "+set", "developer", "1",
    "+set", "logfile", "2",
    "+set", "g_gametype", "coop",
    "+set", "codol_admissionRequired", "0",
    "+map", "mp_firingrange"
]

print("Executing test run of codol_dedrun_next.exe...")
p = subprocess.Popen(cmd, cwd=server_bin_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

try:
    stdout, stderr = p.communicate(timeout=4)
    print("Process exited with code:", p.returncode)
    print("STDOUT:\n", stdout[:2000])
    print("STDERR:\n", stderr[:1000])
except subprocess.TimeoutExpired:
    print("Process is STILL RUNNING after 4 seconds (SUCCESS: server spawned!)")
    p.terminate()
    stdout, stderr = p.communicate()
    print("Captured STDOUT:\n", stdout[:2000])
