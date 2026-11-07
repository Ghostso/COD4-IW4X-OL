#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
suspend_host_redirect.py -- hostname redirection without injection.

Creates the game suspended, obtains a read/write handle before ACE arms, then
overwrites selected hostname strings in the mapped image with equal-length
loopback placeholders. Because the strings are the same length, no relocation
is needed and nothing is injected into the process.

This is observation/serving support for building a local CODOL server.

Usage:
    python suspend_host_redirect.py --exe <game.exe> --cwd <dir> --out <dir>
                                    [--seconds 120] [--keep]
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_ALL_ACCESS = 0x001F0FFF
CREATE_SUSPENDED = 0x00000004
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
                ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
                ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
                ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', wt.HANDLE),
                ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [wt.HANDLE, wt.BOOL,
                                           ctypes.POINTER(TOKEN_PRIVILEGES),
                                           wt.DWORD, ctypes.c_void_p,
                                           ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL
k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p,
                               ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p,
                               wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI),
                               ctypes.c_size_t]
k32.VirtualProtectEx.restype = wt.BOOL
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                 wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ResumeThread.argtypes = [wt.HANDLE]

HOSTS = [
    b'ied-tqos.qq.com', b'tqos.gamesafe.qq.com',
    b'cod4master.activision.com', b'stun.us.demonware.net',
    b'stun.eu.demonware.net', b'stun.jp.demonware.net',
    b'stun.au.demonware.net', b'stun1-tub.codol.qq.com',
    b'exp.tcls.qq.com', b'dump.gamesafe.qq.com',
    b'down.safe.wegamex.com', b'down.safe.wegamex.com.hk',
    b'intldlgs.qq.com',
]

# The original host string is replaced in-place with a NUL-terminated loopback
# address; leftover bytes are NUL-padded so the C string terminates correctly.
def redirect_bytes(src):
    out = b'127.0.0.1\x00'
    return (out + b'\x00' * (len(src) - len(out)))[:len(src)]


REDIRECTS = {src: redirect_bytes(src) for src in HOSTS}

# NOTE: 80/443 are Windows-reserved on this host (bind -> WinError 10013), and a
# failing bind used to abort the listener set. Keep only ports the client
# actually uses for TQoS/GDP. 8000/UDP is the one that matters for [100].
TCP_PORTS = [3074, 8000, 8081, 10009, 10010, 20810, 28960]
UDP_PORTS = [3074, 8000, 8081, 20810, 28960]


def build_tqos_response(req, variant, advertise_port=8000):
    def be16(v):
        return struct.pack('>H', v)

    seq = struct.unpack_from('>I', req, 12)[0] if len(req) >= 16 else 0
    business = struct.unpack_from('>I', req, 16)[0] if len(req) >= 20 else 100
    if variant == 0:
        body = struct.pack('>II', business, 0)
    elif variant == 1:
        body = struct.pack('>II', business, 0xF)
    elif variant in (3, 4, 5):
        # NOTE: the 0x18=24 in the request is the packet byte length
        # (ruHeadLen 16 + BodyLen 8), NOT a list count. QosResFlag is a bit
        # combination: SCORE|QOSLIST|GAMESVR_LIST|CONNDIP_LIST = 0xF.
        # Variant 3/4/5 differ only in how the GameSvr/ConndIPPort lists are
        # laid out; keep them small and structurally valid.
        flag = 0xF
        if variant == 3:
            # Empirically this is the response shape that makes the client
            # enter the 8081 QoS stage (268-byte datagram): 24 entries.
            entry = struct.pack('>IHI', 0x7F000001, 8000, 0)
            body = (struct.pack('>II', business, flag) +
                    struct.pack('>HH', 0, 24) + entry * 24)
        elif variant == 4:
            # One GameSvr: GameSvrIPList(str) + ConndIP(u32) + ConndPort(u16) + Score(u32)
            ip = b'127.0.0.1\x00'
            gs = (struct.pack('>H', len(ip)) + ip +
                  struct.pack('>I', 0x7F000001) +
                  struct.pack('>H', advertise_port) +
                  struct.pack('>I', 0))
            body = (struct.pack('>II', business, flag) +
                    struct.pack('>H', 1) + gs +
                    struct.pack('>H', 1) +
                    struct.pack('>IHI', 0x7F000001, advertise_port, 0))
        else:
            # ConndIPPortNum=1, then GameSvrList
            ip = b'127.0.0.1\x00'
            gs = (struct.pack('>H', len(ip)) + ip +
                  struct.pack('>I', 0x7F000001) +
                  struct.pack('>H', advertise_port) +
                  struct.pack('>I', 0))
            body = (struct.pack('>II', business, flag) +
                    struct.pack('>H', 1) +
                    struct.pack('>IHI', 0x7F000001, advertise_port, 0) +
                    struct.pack('>H', 1) + gs)
    else:
        ip = b'127.0.0.1\x00'
        body = (struct.pack('>II', business, 0xF) + be16(1) + be16(len(ip)) + ip +
                struct.pack('>I', 0x7F000001) + be16(advertise_port) +
                struct.pack('>I', 0))
    header = b'ur' + struct.pack('>HHHHH', 16, len(body), 4, 0, 0) + struct.pack('>I', seq)
    return header + body


def parse_ur(data):
    out = {'magic': data[:2].decode('ascii', 'replace')}
    if len(data) >= 16:
        h = struct.unpack_from('>HHHHH', data, 2)
        out.update({'ruHeadLen': h[0], 'bodyLen': h[1], 'cmd': h[2],
                    'protoVer': h[3], 'reserved': h[4],
                    'seq': struct.unpack_from('>I', data, 12)[0]})
    if len(data) >= 20:
        out['businessID'] = struct.unpack_from('>I', data, 16)[0]
    return out


def build_qos8081_reply(req, mode):
    """Candidate replies for the encrypted QoS measurement channel."""
    if mode == 'echo':
        return bytes(req)
    if mode == 'echotail':
        # Echo the payload but clear the trailing u16 pair pattern.
        out = bytearray(req)
        if len(out) >= 4:
            out[-4] = 0
            out[-3] = 0
        return bytes(out)
    if mode == 'zero84':
        return bytes(84)
    if mode == 'zerosame':
        return bytes(len(req))
    return bytes(req)


def enable_debug():
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        return False, ctypes.get_last_error()
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


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield base, size
        nxt = base + size
        if nxt <= addr:
            return
        addr = nxt


def write_bytes(h, va, data):
    old = wt.DWORD()
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(data), 0x40,
                                ctypes.byref(old)):
        return False
    written = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(va), data, len(data),
                                ctypes.byref(written))
    k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(data), old.value,
                         ctypes.byref(old))
    return bool(ok) and written.value == len(data)


TCLS_SHM_FMT = 'TCLS_SHAREDMEMEMORY%d'
TCLS_SHM_SIZE = 0x7AC
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
FILE_MAP_ALL_ACCESS = 0x000F001F


def create_tcls_handoff(pid, log):
    """Create the client's real TCLS handoff block before ResumeThread.

    Reverse result (SHM_HANDOFF_REVERSE.md):
      name  = TCLS_SHAREDMEMEMORY<pid>   (note the MEMEMORY typo)
      size  = 0x7AC
      +0x004 = 0x7AC
      +0x008/+0x00C = len1/len2 must be 0, otherwise the client dereferences
                      random block1 fields and crashes.
    Do not create TCLS_TASMEMORY_ / TCLS_SHELLMEMORY_ (crash path).
    """
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    name = TCLS_SHM_FMT % pid
    payload = bytearray(TCLS_SHM_SIZE)
    struct.pack_into('<I', payload, 0x000, 1)       # ready
    struct.pack_into('<I', payload, 0x004, TCLS_SHM_SIZE)
    # Embed the captured real TCLS ServerDir response in block1 when present.
    # block1 lives at +0x010 and is 0x400 bytes; the captured response is 774.
    dir_resp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'tcls_dirtree_response.bin')
    len1 = 0
    if os.path.isfile(dir_resp):
        blob = open(dir_resp, 'rb').read()
        if 0 < len(blob) <= 0x400:
            payload[0x010:0x010 + len(blob)] = blob
            len1 = len(blob)
    struct.pack_into('<I', payload, 0x008, len1)    # len1
    struct.pack_into('<I', payload, 0x00C, 0)       # len2
    h = k32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, 0x04, 0,
                               TCLS_SHM_SIZE, name)
    if not h:
        log('TCLS handoff CreateFileMappingW(%s) failed err=%d'
            % (name, ctypes.get_last_error()))
        return None
    p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, TCLS_SHM_SIZE)
    if not p:
        log('TCLS handoff MapViewOfFile(%s) failed err=%d'
            % (name, ctypes.get_last_error()))
        k32.CloseHandle(h)
        return None
    ctypes.memmove(p, bytes(payload), TCLS_SHM_SIZE)
    k32.UnmapViewOfFile(p)
    log('TCLS handoff created: %s size=0x%X ready=1 len1=%d len2=0'
        % (name, TCLS_SHM_SIZE, len1))
    return h


def dump_full_image(h, out_dir, lo=0x00400000, hi=0x00E65000,
                    seconds=20.0, step=2.0):
    """Full-image dump using a pre-ACE PROCESS_ALL_ACCESS handle.

    The ordinary attach path (OpenProcess after the game is running) is denied
    by ACE on this title, so this function is intentionally called from the
    suspended-launch/early-handle path.
    """
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, 'fullimage.log')
    logf = open(log_path, 'w', encoding='utf-8')
    best = None
    best_nz = -1
    best_t = 0.0
    t0 = time.time()

    def say(msg):
        logf.write(msg + '\n')
        logf.flush()
        print(msg, flush=True)

    while time.time() - t0 < seconds:
        el = time.time() - t0
        blob = bytearray(hi - lo)
        for base, size in regions(h):
            a = max(base, lo)
            b = min(base + size, hi)
            if b <= a:
                continue
            data = read_some(h, a, b - a)
            if data:
                blob[a - lo:a - lo + len(data)] = data
        nz = sum(1 for v in blob if v)
        say('t=%.2fs nonzero=%d' % (el, nz))
        if nz > best_nz:
            best = bytes(blob)
            best_nz = nz
            best_t = el
        time.sleep(step)

    if best is not None:
        path = os.path.join(out_dir, 'image_best.bin')
        with open(path, 'wb') as fh:
            fh.write(best)
        say('BEST t=%.2fs nonzero=%d -> %s' % (best_t, best_nz, path))
    logf.close()
    return best_nz


def start_listeners(out_dir, stop_evt, variant=-1, qos_mode='',
                    advertise_port=8000):
    trace = open(os.path.join(out_dir, 'local_listeners.jsonl'), 'w',
                 encoding='utf-8')

    def emit(obj):
        trace.write(json.dumps(obj, ensure_ascii=False) + '\n')
        trace.flush()

    def tcp_loop(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            s.listen(16)
            s.settimeout(0.5)
        except Exception as exc:
            emit({'proto': 'tcp', 'port': port, 'listen_error': repr(exc)})
            return
        while not stop_evt.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            try:
                conn.settimeout(0.5)
                data = conn.recv(8192)
                emit({'proto': 'tcp', 'port': port, 'peer': addr,
                      'data_hex': data.hex(), 'len': len(data)})
                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
            except Exception as exc:
                emit({'proto': 'tcp', 'port': port, 'error': repr(exc)})
            try:
                conn.close()
            except Exception:
                pass
        s.close()

    def udp_loop(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('127.0.0.1', port))
            s.settimeout(0.5)
        except Exception as exc:
            emit({'proto': 'udp', 'port': port, 'listen_error': repr(exc)})
            return
        while not stop_evt.is_set():
            try:
                data, addr = s.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception:
                break
            emit({'proto': 'udp', 'port': port, 'peer': addr,
                  'data_hex': data.hex(), 'len': len(data)})
            if port == 8081 and addr and len(addr) >= 2:
                try:
                    out = subprocess.run(
                        ['netstat', '-ano', '-p', 'udp'],
                        capture_output=True, text=True, timeout=5).stdout
                    needle = ':' + str(addr[1])
                    owner_lines = [l.strip() for l in out.splitlines()
                                   if needle in l]
                    emit({'proto': 'udp', 'port': port,
                          'peer_port': addr[1],
                          'owner_lines': owner_lines[:10]})
                except Exception as exc:
                    emit({'proto': 'udp', 'port': port,
                          'owner_lookup_error': repr(exc)})
            if variant >= 0 and data[:2] == b'ur':
                try:
                    resp = build_tqos_response(data, variant, advertise_port)
                    s.sendto(resp, addr)
                    emit({'proto': 'udp', 'port': port, 'sent_reply_len': len(resp),
                          'sent_hex': resp.hex(), 'to': list(addr),
                          'req_parsed': parse_ur(data)})
                except Exception as exc:
                    emit({'proto': 'udp', 'port': port, 'reply_error': repr(exc)})
            elif qos_mode and port in (8081, 3074) and data[:2] != b'ur':
                try:
                    resp = build_qos8081_reply(data, qos_mode)
                    s.sendto(resp, addr)
                    emit({'proto': 'udp', 'port': port, 'sent_qos_len': len(resp),
                          'mode': qos_mode, 'req_len': len(data), 'to': list(addr)})
                except Exception as exc:
                    emit({'proto': 'udp', 'port': port, 'qos_reply_error': repr(exc)})
        s.close()

    threads = []
    for p in TCP_PORTS:
        t = threading.Thread(target=tcp_loop, args=(p,), daemon=True)
        t.start()
        threads.append(t)
    for p in UDP_PORTS:
        t = threading.Thread(target=udp_loop, args=(p,), daemon=True)
        t.start()
        threads.append(t)
    return trace, threads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=120.0)
    ap.add_argument('--patch-seconds', type=float, default=35.0)
    ap.add_argument('--dry-run', action='store_true',
                    help='find and report targets without rewriting')
    ap.add_argument('--no-listeners', action='store_true',
                    help='do not bind local capture ports')
    ap.add_argument('--no-handoff', action='store_true',
                    help='do not create TCLS_SHAREDMEMEMORY<pid>')
    ap.add_argument('--reply-variant', type=int, default=-1,
                    help='>=0 enables synthetic TQoS replies with that variant')
    ap.add_argument('--qos-mode', default='',
                    help='echo|echotail|zero84|zerosame reply mode for 8081 traffic')
    ap.add_argument('--advertise-port', type=int, default=8000)
    ap.add_argument('--full-image', action='store_true',
                    help='dump the full engine image using the pre-ACE handle')
    ap.add_argument('--full-image-out', default='',
                    help='output directory for --full-image')
    ap.add_argument('--full-image-delay', type=float, default=6.0)
    ap.add_argument('--full-image-seconds', type=float, default=18.0)
    ap.add_argument('--full-image-step', type=float, default=2.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    log = open(os.path.join(args.out, 'host_redirect.log'), 'w', encoding='utf-8')

    def say(msg):
        log.write(msg + '\n')
        log.flush()
        print(msg, flush=True)

    ok, err = enable_debug()
    say('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % args.exe
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(args.exe, buf, None, None, True,
                              CREATE_SUSPENDED, None, args.cwd,
                              ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit('CreateProcess failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    say('created suspended pid=%d' % pid)

    h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    say('pre-arm OpenProcess(ALL_ACCESS) -> %s err=%d'
        % (h, ctypes.get_last_error()))
    if not h:
        k32.ResumeThread(pi.hThread)
        raise SystemExit('need write access')

    # Patch hostnames while still suspended.
    found = {}
    stop_evt = threading.Event()
    listener_trace = None
    if not args.no_listeners:
        listener_trace, listener_threads = start_listeners(
            args.out, stop_evt, args.reply_variant, args.qos_mode,
            args.advertise_port)
        say('local listeners started tcp=%s udp=%s' % (TCP_PORTS, UDP_PORTS))
    for base, size in regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = read_some(h, base + off, want)
            if data:
                for src, dst in REDIRECTS.items():
                    start = 0
                    while True:
                        i = data.find(src, start)
                        if i < 0:
                            break
                        va = base + off + i
                        found.setdefault(src.decode(), []).append(va)
                        if not args.dry_run:
                            good = write_bytes(h, va, dst)
                            say('patch %s@0x%08X -> %s ok=%s'
                                % (src.decode(), va, dst.decode(), good))
                        start = i + 1
            off += want
    with open(os.path.join(args.out, 'redirect_targets.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({k: ['0x%08X' % v for v in vs] for k, vs in found.items()},
                  fh, indent=2)
    say('targets: %s' % {k: len(v) for k, v in found.items()})

    handoff = None
    if not args.no_handoff:
        handoff = create_tcls_handoff(pid, say)
    k32.ResumeThread(pi.hThread)
    say('resumed')
    t0 = time.time()
    if args.full_image:
        if args.full_image_delay > 0:
            time.sleep(args.full_image_delay)
        out_dir = args.full_image_out or os.path.join(args.out, 'fullimage')
        say('full-image dump start out=%s' % out_dir)
        dump_full_image(h, out_dir, seconds=args.full_image_seconds,
                        step=args.full_image_step)
        say('full-image dump end')
    patched = {k: set(v) for k, v in found.items()}
    next_scan = 0.0
    while time.time() - t0 < args.seconds:
        if time.time() - t0 >= next_scan and time.time() - t0 <= args.patch_seconds:
            next_scan = time.time() - t0 + 0.5
            new_count = 0
            for base, size in regions(h):
                off = 0
                while off < size:
                    want = min(0x100000, size - off)
                    data = read_some(h, base + off, want)
                    if data:
                        for src, dst in REDIRECTS.items():
                            start = 0
                            while True:
                                i = data.find(src, start)
                                if i < 0:
                                    break
                                va = base + off + i
                                if va not in patched.setdefault(src.decode(), set()):
                                    patched[src.decode()].add(va)
                                    good = write_bytes(h, va, dst)
                                    say('late-patch %s@0x%08X -> %s ok=%s'
                                        % (src.decode(), va, dst.decode(), good))
                                    new_count += 1
                                start = i + 1
                    off += want
            if new_count:
                say('late-patch round: %d new occurrence(s)' % new_count)
        time.sleep(0.25)
    stop_evt.set()
    time.sleep(1)
    if listener_trace is not None:
        listener_trace.close()
    say('done')
    log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
