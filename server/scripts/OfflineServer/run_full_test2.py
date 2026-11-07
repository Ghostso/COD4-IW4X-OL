import subprocess
import time
import os
import sys
import json

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OFFLINE = os.path.join(ROOT, "OfflineServer")
LOBBY_SRV = os.path.join(OFFLINE, "lobby_server")
GAME_SBX = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")
EXE_PATH = os.path.join(GAME_SBX, "codoMP_client_shipRetail.exe")

def start_server(script_name, bind, port, log_name):
    log_path = os.path.join(OFFLINE, "logs", log_name)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    proc = subprocess.Popen(
        [
            sys.executable, "-X", "utf8",
            os.path.join(LOBBY_SRV, script_name),
            "--cert-dir", LOBBY_SRV,
            "--bind", bind,
            "--port", str(port),
            "--log", log_path
        ],
        cwd=ROOT,
        stdout=open(os.path.join(OFFLINE, "logs", f"{script_name}.out.txt"), "w"),
        stderr=subprocess.STDOUT
    )
    return proc

def build_launcher_args(sandbox):
    ad_path = os.path.join(sandbox, "WeGameLauncher", "game", "ad_login.png")
    ad_video = os.path.join(sandbox, "WeGameLauncher", "game", "ad_mini.mp4")
    payload = {
        "ad_begin": "",
        "ad_end": "",
        "ad_path": ad_path.replace("\\", "\\\\"),
        "ad_type": 1,
        "ad_url": "http://codol.qq.com/",
        "ad_video": ad_video.replace("\\", "\\\\"),
        "click_btn_show_txt": "\u67e5\u770b\u8be6\u60c5",
        "custom": "26",
        "game_id": 29,
        "launcher_ver": "1.3.0.76"
    }
    json_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    # The original ps1 does not escape backslashes in json? It just concatenates path with single backslashes.
    # We'll keep single backslashes as in file system.
    json_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).replace("\\\\", "\\")
    args = f'-launcher={json_str} StartFor=29 AddPath="{sandbox}"'
    return args

def main():
    os.makedirs(os.path.join(OFFLINE, "logs"), exist_ok=True)

    print("[*] Starting lobby_probe_server on 127.0.0.1:8443")
    probe = start_server("lobby_probe_server.py", "127.0.0.1", 8443, "lobby_probe.jsonl")
    print("[*] Starting lobby_socket_server on 127.0.0.2:8444")
    socket_srv = start_server("lobby_socket_server.py", "127.0.0.2", 8444, "lobby_socket.jsonl")

    time.sleep(3)

    for name, p in [("probe", probe), ("socket", socket_srv)]:
        if p.poll() is not None:
            print(f"[!] {name} server exited early with code {p.returncode}")
            return 1
    print("[*] Both servers alive")

    # Build launcher args like WeGame does
    launcher_args = build_launcher_args(GAME_SBX)
    print("[*] Launcher args:", launcher_args)

    # Launch game directly with those args, working dir = sandbox
    print("[*] Launching game exe directly with WeGame-style args")
    game_proc = subprocess.Popen(
        [EXE_PATH] + launcher_args.split(),
        cwd=GAME_SBX,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    deadline = time.time() + 60
    while time.time() < deadline:
        if game_proc.poll() is not None:
            out, err = game_proc.communicate()
            print(f"[*] Game process exited with code {game_proc.returncode}")
            if out:
                print("STDOUT:", out.decode(errors="ignore")[:2000])
            if err:
                print("STDERR:", err.decode(errors="ignore")[:2000])
            break
        for log_file, label in [
            (os.path.join(OFFLINE, "logs", "lobby_probe.jsonl"), "probe"),
            (os.path.join(OFFLINE, "logs", "lobby_socket.jsonl"), "socket")
        ]:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if any(k in line for k in ("tls_ok", "http", "roundtrip", "auth_task")):
                            print(f"[+] {label} activity: {line.strip()}")
        time.sleep(2)

    for p in (probe, socket_srv, game_proc):
        if p.poll() is None:
            p.terminate()
    print("[*] Test finished")
    return 0

if __name__ == "__main__":
    sys.exit(main())