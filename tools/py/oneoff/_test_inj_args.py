import subprocess, os

game_dir = r"E:\CODOL_SANDBOX\RUN001"
injector = os.path.join(game_dir, "Ayria", "Injector32.exe")
target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")

log_path = os.path.join(game_dir, "Ayria", "Logs", "CODOLLauncher-client-1.log")
with open(log_path, "w") as log:
    res = subprocess.run([injector, target], cwd=game_dir, stdout=log, stderr=subprocess.STDOUT)

print("Return code:", res.returncode)
print("Log output:")
print(open(log_path).read())
