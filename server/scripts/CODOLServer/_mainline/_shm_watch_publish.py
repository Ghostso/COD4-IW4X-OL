# -*- coding: utf-8 -*-
"""Wait for codoMP_client_shipRetail to appear, then publish the TAS SHM.

健康轮(IFS1_ELEVATED_20261005_113927)是通过 _multiround.py 的等待线程发布
shm 的; 直跑 _e57a5c_experiment.py 时没有这一步。本脚本补上: 轮询游戏进程,
出现即发布, 然后保持映射存活直到被终止。

Usage:
    python _shm_watch_publish.py [image_path]
"""
import subprocess
import sys
import time

import _z7_publish_shm as pub

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
DEFAULT_IMAGE = (ROOT + r"\CODOLServer\_subagents\_tenproxy_shm_fixed.bin")


def game_pid():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process codoMP_client_shipRetail -EA SilentlyContinue).Id"],
            capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    s = (out.stdout or "").strip()
    return int(s) if s.isdigit() else None


def main() -> int:
    # argv[1]=image (空串则用默认), argv[2]=delay 秒
    image = (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1]
             else DEFAULT_IMAGE)
    # 延后到游戏起来后 delay 秒再发布。实测游戏刚起就注入会让它在 10 s 内
    # 早退; 与观察器 PokeLobbyGlobals(t>=20) 同刻发布才安全。
    try:
        delay = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
    except ValueError:
        delay = 20.0
    print("[shm] image=%s delay=%.0fs" % (image, delay), flush=True)
    t0 = None
    for _ in range(600):
        pid = game_pid()
        if pid:
            if t0 is None:
                t0 = time.time()
                print("[shm] game pid=%s, waiting %.0fs" % (pid, delay),
                      flush=True)
            if time.time() - t0 >= delay:
                r = pub.publish_shm(pid, image)
                print("[shm] published pid=%s -> %s" % (pid, r), flush=True)
                # 保持进程存活, 映射不撤销
                while True:
                    time.sleep(2.0)
                    if game_pid() is None:
                        print("[shm] game gone, exit", flush=True)
                        return 0
            if game_pid() is None:
                print("[shm] game exited before publish", flush=True)
                return 1
        time.sleep(0.5)
    print("[shm] game process not found", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
