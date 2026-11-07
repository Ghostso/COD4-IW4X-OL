import subprocess, time, os, json
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697")
DIAG = ROOT.parent
exe = ROOT / "native" / "bin2697" / "codol_dedrun.exe"
registration = ROOT / "evidence" / "client-registration2697.txt"
attachment_map = ROOT / "evidence" / "attachment-registry2697.txt"

assert exe.is_file(), f"exe missing: {exe}"
assert registration.is_file(), f"registration missing: {registration}"
assert attachment_map.is_file(), f"attachment_map missing: {attachment_map}"

home = ROOT / "native-server-live"
home.mkdir(parents=True, exist_ok=True)
profiles = home / "local-profiles"
profiles.mkdir(parents=True, exist_ok=True)
scripts = ROOT / "scripts"

os.environ["CODOL_TARGET2697_ATTACHMENT_REGISTRY"] = str(attachment_map)

values = dict(
    dedicated="1",
    fs_basepath=str(ROOT / "runtime-assets"),
    fs_homepath=str(home),
    codol_clientExe=str(DIAG / "aplib-recovered" / "codol2697-static-candidate.bin"),
    codol_target2697="1",
    codol_target2697Registration=str(registration),
    codol_zonePath=str(ROOT / "runtime-assets" / "chinese"),
    loc_language="11",
    net_ip="127.0.0.1",
    net_port="28960",
    sv_maxclients="1",
    logfile="2",
    developer="1",
    onlinegame="1",
    xblive_privatematch="1",
    scr_forcerankedmatch="0",
    debug_challenges="0",
    codol_admissionRequired="0",
    codol_securityKeyPath="",
    codol_localChannel2697="1",
    codol_profilePath=str(profiles),
    scr_codol_bots="0",
    sv_fps="60",
    codol_zoneType="mp",
    g_gametype="war",
    codol_scriptPath=str(scripts),
    codol_scriptOverlay=str(scripts),
    codol_scriptNativeOverlay=str(ROOT / "script-overlay2697")
)

cmd = [str(exe)]
for k, v in values.items():
    cmd += ["+set", k, str(v)]
cmd += ["+map", "mp_firingrange", "+codol_checktargetpublication"]

print("Spawning Native Dedicated Server (codol_dedrun.exe) on UDP 28960...")
log_file = home / "console.log"
with log_file.open("wb") as log:
    proc = subprocess.Popen(
        cmd,
        cwd=home,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=dict(os.environ, CODOL_MATCH_DIAGNOSTICS="1"),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

print(f"Server process started (PID={proc.pid})! Waiting 6 seconds for level load...")
time.sleep(6)

print("Checking server status:")
is_alive = proc.poll() is None
print(f"  Process alive: {is_alive} (PID={proc.pid})")

# Check if UDP 28960 is bound
net = subprocess.run(["netstat", "-ano", "-p", "UDP"], capture_output=True, text=True)
for line in net.stdout.splitlines():
    if ":28960" in line:
        print("  Listening socket:", line.strip())

# Check console log
if log_file.exists():
    text = log_file.read_text(encoding="utf-8", errors="replace")
    print("\n--- console.log tail ---")
    for l in text.splitlines()[-25:]:
        print(" ", l)
