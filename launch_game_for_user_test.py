# -*- coding: utf-8 -*-
"""
launch_game_for_user_test.py — 启动 3.19 游戏与全套服务并自动将游戏窗口置顶
"""

import sys, os, time, subprocess, threading, ctypes

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
AGENT_CLIENT = os.path.join(ROOT, "CODOLServer", "_mainline", "agent_client.py")
RUN_ALL = os.path.join(ROOT, "REF_LOBBY_KIT", "run_all.py")
LOBBY_LOG = os.path.join(ROOT, "REF_LOBBY_KIT", "lobby_srv.log")
BATTLE_LOG = os.path.join(ROOT, "REF_LOBBY_KIT", "_battle_out.txt")
COMBAT_LOG = os.path.join(ROOT, "CODOL-Combat-Server-v0.1", "logs", "firingrange_live.log")

def bring_window_to_foreground():
    user32 = ctypes.windll.user32
    print("[*] 正在等待游戏窗口出现并置顶...", flush=True)
    for _ in range(90):
        time.sleep(1.0)
        # Search for window title containing "使命召唤"
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        found = [None]
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "使命召唤" in buf.value or "codo" in buf.value.lower():
                        found[0] = hwnd
                        return False
            return True
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if found[0]:
            hwnd = found[0]
            print(f"[+] 找到游戏窗口 HWND=0x{hwnd:X}，执行置顶！", flush=True)
            user32.ShowWindow(hwnd, 9) # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            break

def monitor_telemetry(stop_event):
    last_combat_size = os.path.getsize(COMBAT_LOG) if os.path.exists(COMBAT_LOG) else 0
    last_battle_size = os.path.getsize(BATTLE_LOG) if os.path.exists(BATTLE_LOG) else 0
    last_lobby_size = os.path.getsize(LOBBY_LOG) if os.path.exists(LOBBY_LOG) else 0

    while not stop_event.is_set():
        time.sleep(0.5)
        # Monitor Combat Server log
        if os.path.exists(COMBAT_LOG):
            sz = os.path.getsize(COMBAT_LOG)
            if sz > last_combat_size:
                with open(COMBAT_LOG, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_combat_size)
                    new_text = f.read()
                    last_combat_size = sz
                    for ln in new_text.splitlines():
                        if any(k in ln for k in ["RX", "STAT", "OOB", "DTLS", "GAMESTATE", "SNAPSHOT", "USERCMD", "NETCHAN", "WEAPON"]):
                            print(f"[COMBAT_SRV] {ln}", flush=True)

        # Monitor Lobby Log
        if os.path.exists(LOBBY_LOG):
            sz = os.path.getsize(LOBBY_LOG)
            if sz > last_lobby_size:
                with open(LOBBY_LOG, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_lobby_size)
                    new_text = f.read()
                    last_lobby_size = sz
                    for ln in new_text.splitlines():
                        if any(k in ln for k in ["firingrange", "booking", "mmstart", "session", "28960"]):
                            print(f"[LOBBY_SRV] {ln}", flush=True)

def main():
    print("=" * 70)
    print("启动 CODOL 3.19 实机对局全栈服务（大厅 + 3.19 独立战斗服 + 客户端）")
    print("=" * 70)

    # 1. 启动窗口置顶后台线程
    # [DISABLED] Never grab foreground or lock desktop input queue
    # t_fg = threading.Thread(target=bring_window_to_foreground, daemon=True)
    # t_fg.start()

    # 2. 启动遥测监控后台线程
    stop_mon = threading.Event()
    t_mon = threading.Thread(target=monitor_telemetry, args=(stop_mon,), daemon=True)
    t_mon.start()

    # 3. 运行 run_all.py (分配 1800 秒 = 30 分钟窗口)
    cmd = [
        sys.executable, "-X", "utf8", AGENT_CLIENT, "run",
        sys.executable, "-X", "utf8", RUN_ALL,
        "--secs", "1800", "--out", "n10_interactive_test.txt", "--force", "--no-certs"
    ]
    print(f"执行启动链: {' '.join(cmd)}", flush=True)
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT)
        proc.wait()
    except KeyboardInterrupt:
        print("\n收到退出指令，正在停止服务...", flush=True)
    finally:
        stop_mon.set()
        print("测试流程结束。")

if __name__ == "__main__":
    main()
