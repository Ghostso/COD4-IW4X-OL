# -*- coding: utf-8 -*-
"""Launch the game and WATCH THE ACTUAL WINDOWS at high frequency.

Purpose: the in-game "cannot connect to the lobby service" popup does NOT
auto-dismiss, so a live process is not evidence of success.  We must observe
the real top-level windows, not just the observer's log.

When a popup is seen:
  * record pid / class / text
  * dump every window of that process (to catch the dialog's children)
  * kill the game tree and stop

Writes: CODOLServer/lobby3074/logs/popup_watch_<ts>.log
"""
import ctypes
import ctypes.wintypes as w
import json
import os
import socket
import subprocess
import sys
import threading
import time

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGD = os.path.join(ROOT, "CODOLServer", "lobby3074", "logs")

# Window classes / texts that indicate the lobby-connection failure dialog.
POPUP_CLASSES = {"#32770", "SoPY_MessageBox"}
POPUP_TEXT_KEYS = [
    "无法连接大厅服务", "与大厅服务失去连接", "连接大厅服务失败",
    "无法连接", "失去连接", "connection", "lobby",
]


def win_text(h):
    n = u32.GetWindowTextLengthW(h)
    if n == 0:
        return ""
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(h, b, n + 1)
    return b.value


def win_class(h):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, b, 256)
    return b.value


def win_pid(h):
    p = w.DWORD()
    u32.GetWindowThreadProcessId(h, ctypes.byref(p))
    return p.value


def enum_windows():
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

    def cb(h, l):
        out.append(h)
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def snapshot():
    """Return list of (pid, class, text, visible, hwnd) for all top-level."""
    res = []
    for h in enum_windows():
        res.append((win_pid(h), win_class(h), win_text(h),
                    bool(u32.IsWindowVisible(h)), h))
    return res


def child_windows(hparent):
    res = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

    def cb(h, l):
        res.append((win_class(h), win_text(h), bool(u32.IsWindowVisible(h))))
        return True

    u32.EnumChildWindows(hparent, WNDENUMPROC(cb), 0)
    return res


def game_pids():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process | Where-Object {$_.ProcessName -match "
         "'codoMP_client_shipRetail|IIPSHostApp|AboProbe'} | "
         "ForEach-Object { $_.Id }"],
        capture_output=True)
    return [int(x) for x in r.stdout.decode().split() if x.strip().isdigit()]


def kill_game_tree():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process | Where-Object {$_.ProcessName -match "
         "'codoMP_client_shipRetail|AboProbe|IIPSHostApp|TP3Helper'} | "
         "Stop-Process -Force -ErrorAction SilentlyContinue"],
        capture_output=True)


def agent_run(argv, timeout=600):
    st = json.load(open(os.path.join(ROOT, "CODOLServer", "logs",
                                     "elevated_agent.json"), encoding="utf-8"))
    req = {"action": "run", "argv": argv, "token": st["token"]}
    s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=timeout)
    s.sendall((json.dumps(req) + "\n").encode("utf-8"))
    b = b""
    while not b.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        b += c
    return json.loads(b.decode("utf-8"))


def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    os.makedirs(LOGD, exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    logp = os.path.join(LOGD, "popup_watch_%s.log" % tag)
    fh = open(logp, "w", encoding="utf-8")

    def log(msg):
        line = "%.3f %s" % (time.time(), msg)
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()

    LD = os.path.join(ROOT, "CODOLServer", "logs", "Z7_3074")
    os.makedirs(LD, exist_ok=True)
    argv = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        os.path.join("run_codol_001", "elevated_ifs1_observer.ps1"),
        "-DurationSeconds", str(dur),
        "-Sandbox", os.path.join(ROOT, "run_codol_001",
                                 "sandbox_datafix_20260929"),
        "-TenProxyShm", os.path.join(ROOT, "CODOLServer", "_subagents",
                                     "_tenproxy_shm_fixed.bin"),
        "-PokeLobbyHost", "127.0.0.1", "-PokeLobbyPort", "8443",
        "-PokeE57", "0x00E57A5A",
        "-PokeLobbyGlobals", "1", "-LobbyReadyOnly", "1",
        "-Post83Trace", "1", "-Post83Seconds", "90",
        "-HandshakeReadyFile", os.path.join(LD, "ready.flag"),
        "-HandshakeEchoFile", os.path.join(LD, "echo.txt"),
        "-PatchDelay", "42", "-Patch85Pass", "1",
    ]

    result = {"popup": None}

    def launcher():
        result["r"] = agent_run(argv, timeout=dur + 120)

    th = threading.Thread(target=launcher, daemon=True)
    th.start()
    log("launched, watching windows at 100ms ...")

    seen_classes = {}
    t0 = time.time()
    while th.is_alive() and time.time() - t0 < dur + 30:
        pids = set(game_pids())
        for pid, cls, txt, vis, h in snapshot():
            if pid not in pids:
                continue
            key = (pid, cls, txt)
            if key not in seen_classes:
                seen_classes[key] = time.time() - t0
                log("  WIN pid=%d class=%-26s visible=%s text=%r"
                    % (pid, cls, vis, txt))
            is_popup = cls in POPUP_CLASSES or any(
                k.lower() in txt.lower() for k in POPUP_TEXT_KEYS)
            if is_popup and result["popup"] is None:
                result["popup"] = {"pid": pid, "class": cls, "text": txt,
                                   "t": time.time() - t0}
                log("*** POPUP DETECTED *** t=%.2f pid=%d class=%s text=%r"
                    % (time.time() - t0, pid, cls, txt))
                for cc, ct, cv in child_windows(h):
                    log("      child class=%-24s visible=%s text=%r"
                        % (cc, cv, ct))
                kill_game_tree()
                break
        if result["popup"] is not None:
            break
        time.sleep(0.1)

    th.join(timeout=20)
    r = result.get("r") or {}
    log("agent rc=%s" % r.get("rc"))
    if result["popup"]:
        log("RESULT: POPUP SEEN")
    else:
        log("RESULT: no popup observed during the run")
    log("logfile: %s" % logp)
    fh.close()


if __name__ == "__main__":
    main()
