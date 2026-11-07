import subprocess, os

# Kill any existing combat server or client
for p in ["codoMP_client_shipRetail.exe", "CODOLCombatServer.exe"]:
    subprocess.run(["taskkill", "/F", "/IM", p], capture_output=True)

# Build CODOLCombatServer
cs_root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"
build_ps1 = os.path.join(cs_root, "build", "build.ps1")
res = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", build_ps1], cwd=cs_root, capture_output=True, text=True)
print("Build exit code:", res.returncode)
for l in res.stdout.splitlines()[-10:]:
    print(" ", l)

exe = os.path.join(cs_root, "build", "bin", "CODOLCombatServer.exe")
test_res = subprocess.run([exe, "--selftest"], cwd=cs_root, capture_output=True, text=True)
print("SelfTest exit code:", test_res.returncode)
for l in test_res.stdout.splitlines()[-10:]:
    print(" ", l)
