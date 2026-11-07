#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
elevated_agent.py -- localhost-only privileged helper for CODOL reverse work.

Run this once from an elevated process. It enables SeDebugPrivilege and listens
on 127.0.0.1 for JSON-line commands from the normal Codex session, so memory
scans/dumps can be run without a new UAC prompt each time.

Protocol (one JSON object per line):
    {"token": "...", "action": "ping"}
    {"token": "...", "action": "run", "argv": ["python", "..."],
     "cwd": "...", "timeout": 120}

The listener binds only to 127.0.0.1 and requires the random token written to
CODOLServer\logs\elevated_agent.json.
"""

import ctypes
import ctypes.wintypes as wt
import json
import os
import secrets
import socketserver
import subprocess
import sys
import threading

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                      ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL


def enable_debug_privilege():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        err = ctypes.get_last_error()
        k32.CloseHandle(token)
        return False, err
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(token)
    return bool(ok) and err == 0, err


RUN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(RUN_DIR, 'logs', 'elevated_agent.json')
TOKEN = secrets.token_hex(24)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            line = self.rfile.readline(1024 * 1024)
            req = json.loads(line.decode('utf-8'))
        except Exception as exc:
            self.wfile.write((json.dumps({'ok': False, 'error': str(exc)}) + '\n').encode())
            return
        if req.get('token') != TOKEN:
            self.wfile.write((json.dumps({'ok': False, 'error': 'bad token'}) + '\n').encode())
            return
        action = req.get('action')
        if action == 'ping':
            ok, err = enable_debug_privilege()
            result = {'ok': True, 'pid': os.getpid(), 'debug_privilege': ok,
                      'debug_err': err}
        elif action == 'run':
            argv = req.get('argv')
            if not isinstance(argv, list) or not argv:
                result = {'ok': False, 'error': 'argv must be a non-empty list'}
            else:
                try:
                    proc = subprocess.run(
                        argv, cwd=req.get('cwd') or None,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', timeout=float(req.get('timeout', 300)))
                    result = {'ok': True, 'rc': proc.returncode,
                              'stdout': proc.stdout, 'stderr': proc.stderr}
                except Exception as exc:
                    result = {'ok': False, 'error': repr(exc)}
        else:
            result = {'ok': False, 'error': 'unknown action'}
        self.wfile.write((json.dumps(result, ensure_ascii=False) + '\n').encode())


def main():
    dbg_ok, dbg_err = enable_debug_privilege()
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler)
    port = server.server_address[1]
    state = {'pid': os.getpid(), 'port': port, 'token': TOKEN,
             'debug_privilege': dbg_ok, 'debug_err': dbg_err}
    with open(STATE_PATH, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=2)
    print('elevated_agent pid=%d port=%d debug=%s/%d'
          % (os.getpid(), port, dbg_ok, dbg_err), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
