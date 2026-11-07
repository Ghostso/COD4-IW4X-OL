#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线大厅三合一快速验证：使用固化启动链 launch.ps1，仅运行约 15 秒完成。
"""

import subprocess, time, sys, pathlib

ROOT        = pathlib.Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
OFFLINE_DIR = ROOT / "OfflineServer"
LOBBY_DIR   = OFFLINE_DIR / "lobby_server"
SBX_DIR     = ROOT / "run_codol_001" / "sandbox_ifs1_20260923"
LAUNCH_PS1  = ROOT / "run_codol_001" / "launch.ps1"
LOG_DIR     = OFFLINE_DIR / "logs"

def start_server(script, bind, port, log_name):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [sys.executable, "-X", "utf8",
         str(LOBBY_DIR / script),
         "--cert-dir", str(LOBBY_DIR),
         "--bind", bind,
         "--port", str(port),
         "--log", str(LOG_DIR / log_name)],
        cwd=str(ROOT),
        stdout=open(LOG_DIR / f"{script}.out.txt", "w", encoding="utf-8"),
        stderr=subprocess.STDOUT)

def main():
    print("[===] 离线大厅三合一快速验证")
    probe = start_server("lobby_probe_server.py", "127.0.0.1", 8443, "lobby_probe.jsonl")
    sock  = start_server("lobby_socket_server.py", "127.0.0.2", 8444, "lobby_socket.jsonl")
    time.sleep(1)   # 等 bind

    if probe.poll() is not None or sock.poll() is not None:
        print("[!] 服务端启动失败")
        return 1

    # 固化启动链
    game = subprocess.Popen(
        ["powershell","-NoProfile","-ExecutionPolicy","Bypass",
         "-File", str(LAUNCH_PS1), "-Sandbox", str(SBX_DIR)],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 短暂观察
    time.sleep(8)

    # 检查日志关键字
    keywords = ("tls_ok","http","roundtrip","auth_task")
    def has_kw(path):
        if not path.exists(): return False
        txt = path.read_text(encoding="utf-8", errors="ignore")
        return any(k in txt for k in keywords)

    probe_ok = has_kw(LOG_DIR/"lobby_probe.jsonl")
    sock_ok  = has_kw(LOG_DIR/"lobby_socket.jsonl")

    # 清理
    for p in (probe, sock, game):
        if p.poll() is None:
            p.terminate()
    print("[===] 结果")
    print(f"探针日志含交互：{'是' if probe_ok else '否'}")
    print(f"Socket日志含交互：{'是' if sock_ok else '否'}")
    print(f"游戏退出码：{game.poll() if game.poll() is not None else '运行中'}")
    return 0 if (probe_ok and sock_ok) else 2

if __name__=="__main__":
    sys.exit(main())