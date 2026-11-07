# -*- coding: utf-8 -*-
"""Attach the local native game-server plugin to the already running C client.

The C client is launched by the copied nt10.py chain. This file never creates
another client and never starts the standalone C battle server.
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import pefile
import socket
import struct
import subprocess
import time
from pathlib import Path

TARGET = "codoMP_client_shipRetail.exe"
CHAIN = Path(__file__).resolve().parents[1]
KIT = CHAIN / "kit"
GAME = CHAIN / "game"
LOGS = CHAIN / "logs"
BOOT = GAME / "Ayria" / "Bootstrapper32.dll"
PLUGIN = GAME / "Ayria" / "Plugins" / "CodolGameServer.Localnet32"
GAME_LOGS = GAME / "Ayria" / "Logs"
STILL_ACTIVE = 259

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", ctypes.c_wchar * 256), ("szExePath", ctypes.c_wchar * 260)]

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.restype = wt.BOOL
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.WaitForSingleObject.restype = wt.DWORD
k32.GetExitCodeThread.restype = wt.BOOL
k32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetExitCodeProcess.restype = wt.BOOL
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CloseHandle.restype = wt.BOOL

def process_exit_code(proc):
    code = wt.DWORD(STILL_ACTIVE)
    if not proc or not k32.GetExitCodeProcess(proc, ctypes.byref(code)):
        return None
    return int(code.value)

def write(log, stage, **data):
    row = {"stage": stage, **data}
    log.write(json.dumps(row, ensure_ascii=False) + "\n")
    log.flush()
    print("[native-engine] " + json.dumps(row, ensure_ascii=False), flush=True)

def find_pid():
    raw = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace").stdout
    rows = []
    for line in raw.splitlines():
        cols = [x.strip('"') for x in line.split('","')]
        if cols and cols[0].casefold() == TARGET.casefold():
            rows.append(int(cols[1].replace(",", "")))
    return rows[0] if len(rows) == 1 else None

def find_pids():
    raw = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq " + TARGET, "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace",
    ).stdout
    rows = []
    for line in raw.splitlines():
        cols = [x.strip('"') for x in line.split('","')]
        if cols and cols[0].casefold() == TARGET.casefold():
            try:
                rows.append(int(cols[1].replace(",", "")))
            except (IndexError, ValueError):
                pass
    return rows


def resolve_bootstrapper(game):
    candidates = [
        game / "Ayria" / "Bootstrapper32.dll",
        CHAIN.parent / "COD OL" / "Ayria" / "Bootstrapper32.dll",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]

def module_base(pid, wanted):
    snap = k32.CreateToolhelp32Snapshot(0x08 | 0x10, pid)
    if not snap or snap in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
        return 0
    me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
    base = 0
    if k32.Module32FirstW(snap, ctypes.byref(me)):
        while True:
            if wanted.casefold() in me.szModule.casefold():
                base = int(me.modBaseAddr or 0); break
            if not k32.Module32NextW(snap, ctypes.byref(me)): break
    k32.CloseHandle(snap)
    return base

def load_library(proc, path, loadlib):
    raw = str(path).encode("utf-16le") + b"\0\0"
    mem = k32.VirtualAllocEx(proc, None, len(raw) + 16, 0x3000, 4)
    wrote = ctypes.c_size_t()
    if not mem or not k32.WriteProcessMemory(proc, mem, raw, len(raw), ctypes.byref(wrote)):
        return 0
    tid = wt.DWORD()
    th = k32.CreateRemoteThread(proc, None, 0, ctypes.c_void_p(loadlib), ctypes.c_void_p(mem), 0, ctypes.byref(tid))
    if not th: return 0, ctypes.get_last_error(), None
    k32.WaitForSingleObject(th, 5000)
    code = wt.DWORD(); k32.GetExitCodeThread(th, ctypes.byref(code)); k32.CloseHandle(th)
    # A LoadLibrary thread's return value is only a diagnostic.  The module
    # table is the authoritative source for the loaded base address.
    return int(code.value), ctypes.get_last_error(), int(tid.value)

def loadlibraryw_address(pid):
    base = module_base(pid, "kernel32.dll")
    if not base: return 0
    rva = 0x21960
    try:
        pe = pefile.PE(os.path.join(os.environ.get("SystemRoot", r"C:\\Windows"), "SysWOW64", "kernel32.dll"))
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if exp.name == b"LoadLibraryW": rva = exp.address; break
    except Exception: pass
    return base + rva

def control_packet(msg_type, req_id, payload):
    h = 2166136261
    for b in payload: h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return struct.pack("<IHHIQI", 0x43444C4F, 2, msg_type, len(payload), req_id, h) + payload


def export_rva(path, symbol, fallback):
    """Resolve a plugin export from disk, retaining a known-build fallback."""
    try:
        pe = pefile.PE(str(path), fast_load=False)
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if exp.name and exp.name.decode("ascii", "replace") == symbol:
                return int(exp.address)
    except Exception:
        pass
    return fallback


def call_game_server_enable(proc, plugin_base, plugin_path, log):
    """Enable the in-process native server before waiting on DedicatedControl.

    Loading Localnet32 and installing its frame hook only registers the plugin;
    the network listener is created by CODOL_GameServerSetEnabled(true).
    """
    rva = export_rva(plugin_path, "CODOL_GameServerSetEnabled", 0x1F57F0)
    address = int(plugin_base) + rva
    tid = wt.DWORD(0)
    ctypes.set_last_error(0)
    thread = k32.CreateRemoteThread(
        proc, None, 0, ctypes.c_void_p(address), ctypes.c_void_p(1),
        0, ctypes.byref(tid),
    )
    create_error = ctypes.get_last_error()
    if not thread:
        write(log, "set_enabled", ok=False, address=hex(address), rva=hex(rva),
              thread_id=int(tid.value), create_error=create_error,
              process_exit=process_exit_code(proc))
        return False
    wait_result = k32.WaitForSingleObject(thread, 10000)
    ret = wt.DWORD(0)
    got_ret = bool(k32.GetExitCodeThread(thread, ctypes.byref(ret)))
    thread_error = ctypes.get_last_error()
    k32.CloseHandle(thread)
    write(log, "set_enabled", ok=(got_ret and int(ret.value) == 1),
          address=hex(address), rva=hex(rva), thread_id=int(tid.value),
          wait_result=int(wait_result), return_code=int(ret.value),
          get_exit_code_ok=got_ret, create_error=create_error,
          thread_error=thread_error, process_exit=process_exit_code(proc))
    return bool(got_ret and int(ret.value) == 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=180)
    ap.add_argument("--out", default=str(LOGS / "native_engine_attach.jsonl"))
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--visible-mode", action="store_true",
                    help="大厅客户端模式：只附加模块并记录窗口/大厅状态，不启用 Dedicated 控制端口")
    args = ap.parse_args()
    global GAME, BOOT, PLUGIN, GAME_LOGS
    GAME = Path(args.game_root).resolve()
    BOOT = resolve_bootstrapper(GAME)
    PLUGIN = GAME / "Ayria" / "Plugins" / "CodolGameServer.Localnet32"
    GAME_LOGS = GAME / "Ayria" / "Logs"
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as log:
        deadline = time.monotonic() + args.seconds
        pid = args.pid or None
        while time.monotonic() < deadline:
            current = find_pids()
            if args.pid:
                if args.pid in current:
                    pid = args.pid
                    break
            elif len(current) == 1:
                pid = current[0]
                break
            time.sleep(0.25)
        if not pid:
            write(log, "client_missing", ok=False); return 2
        write(log, "client_found", ok=True, pid=pid)
        proc = k32.OpenProcess(0x1F0FFF, False, pid)
        if not proc:
            write(log, "open_process", ok=False, error=ctypes.get_last_error()); return 3
        write(log, "game_base", base=hex(module_base(pid, TARGET)), base_dll=hex(module_base(pid, "codoMP_client_shipRetailBase.dll")))
        loadlib = loadlibraryw_address(pid)
        write(log, "loadlibraryw", address=hex(loadlib))
        if not loadlib: return 4
        boot = module_base(pid, "Bootstrapper32")
        if not boot:
            boot_thread, boot_error, boot_tid = load_library(proc, BOOT, loadlib)
            # Give the loader a moment, then trust the module table rather
            # than interpreting a failure/exception code as an HMODULE.
            time.sleep(0.25)
            boot = module_base(pid, "Bootstrapper32")
            write(log, "bootstrapper_load", module=hex(boot), path=str(BOOT),
                  thread_return=boot_thread, thread_error=boot_error,
                  thread_id=boot_tid, process_exit=process_exit_code(proc))
        write(log, "bootstrapper", module=hex(boot), path=str(BOOT),
              present=bool(boot))
        plugin = module_base(pid, "CodolGameServer")
        if not plugin:
            plugin_thread, plugin_error, plugin_tid = load_library(proc, PLUGIN, loadlib)
            time.sleep(0.25)
            plugin = module_base(pid, "CodolGameServer")
            write(log, "localnet_plugin_load", module=hex(plugin), path=str(PLUGIN),
                  thread_return=plugin_thread, thread_error=plugin_error,
                  thread_id=plugin_tid, process_exit=process_exit_code(proc))
        write(log, "localnet_plugin", module=hex(plugin), path=str(PLUGIN),
              present=bool(plugin))
        if not plugin: return 5
        hook_log = GAME_LOGS / "CodolGameServer.log"
        hook_deadline = time.monotonic() + (8 if args.visible_mode else 20)
        while time.monotonic() < hook_deadline:
            text = hook_log.read_text(encoding="utf-8", errors="replace") if hook_log.exists() else ""
            if "frame hook installed" in text: break
            if "frame hook failed" in text:
                write(log, "frame_hook", ok=False); return 6
            time.sleep(0.25)
        else:
            write(log, "frame_hook", ok=False, error="timeout")
            if args.visible_mode:
                # Visible Lobby mode does not require the Dedicated frame hook;
                # keep nt10's ordinary Lobby handshake alive and let the parent
                # decide success from lobby_ready/window/exit state.
                write(log, "visible_native_attach", ok=True, pid=pid,
                      frame_hook_timeout=True, dedicated_control_skipped=True)
                end = time.monotonic() + args.seconds
                while time.monotonic() < end:
                    code = process_exit_code(proc)
                    if code != STILL_ACTIVE:
                        write(log, "client_exit", ok=False, code=int(code)); return 8
                    time.sleep(1)
                k32.CloseHandle(proc)
                return 0
            return 6
        write(log, "frame_hook", ok=True)
        if args.visible_mode:
            write(log, "visible_native_attach", ok=True, pid=pid,
                  windows="deferred_to_parent", dedicated_control_skipped=True)
            end = time.monotonic() + args.seconds
            while time.monotonic() < end:
                code = process_exit_code(proc)
                if code != STILL_ACTIVE:
                    write(log, "client_exit", ok=False, code=int(code)); return 8
                time.sleep(1)
            k32.CloseHandle(proc)
            return 0
        if not call_game_server_enable(proc, plugin, PLUGIN, log):
            return 7
        ctrl = None
        for _ in range(120):
            try:
                ctrl = socket.create_connection(("127.0.0.1", 28961), timeout=1)
                break
            except OSError: time.sleep(0.5)
        if not ctrl:
            write(log, "dedicated_control", ok=False); return 7
        key = bytes.fromhex((KIT / "battle_security_key.txt").read_text(encoding="ascii").strip()) if (KIT / "battle_security_key.txt").exists() else b"\x01" * 16
        try:
            ctrl.sendall(control_packet(4, 1, bytes([0x13,0x08,0x10,0,0,0]) + key))
            hdr = ctrl.recv(24)
            status = struct.unpack("<IHHIQI", hdr)[2] if len(hdr) == 24 else -1
            write(log, "configure_session", ok=(status == 0), status=status)
        finally:
            ctrl.close()
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            code = wt.DWORD(); k32.GetExitCodeProcess(proc, ctypes.byref(code))
            if code.value != 259:
                write(log, "client_exit", ok=False, code=int(code.value)); return 8
            time.sleep(1)
        k32.CloseHandle(proc)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
