#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
key_capture_patch.py -- deterministically capture the 8081 AES key.

ProtocalHandler.dll builds the per-session 16-byte key and copies it to
context+0x50, then calls the AES key setup at RVA 0x7AA80 from RVA 0x63E67.

We create the game suspended, get an ALL_ACCESS handle before ACE arms, wait
for ProtocalHandler.dll to be mapped, briefly suspend the process, and replace
the 5-byte call at RVA 0x63E67 with a call to a tiny stub. The stub copies the
16 bytes at [edx] (context+0x50) into an RWX scratch page and sets a flag, then
chains to the original AES setup. We poll the scratch page, read the key, and
restore the original bytes.

Run elevated. This patches only the game's own process memory, in-memory only.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import suspend_host_redirect as S  # noqa: E402

k32 = S.k32
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)

PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000

CALLSITE_RVA = 0x63E64          # pattern: 89 72 0C E8 14 6C 01 00
CALL_RVA = 0x63E67              # E8 ...
ORIGINAL_SETKEY_RVA = 0x7AA80
PATTERN = bytes.fromhex('89720ce8146c0100')

ntdll.NtSuspendProcess.argtypes = [wt.HANDLE]
ntdll.NtSuspendProcess.restype = ctypes.c_long
ntdll.NtResumeProcess.argtypes = [wt.HANDLE]
ntdll.NtResumeProcess.restype = ctypes.c_long
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                               wt.DWORD, wt.DWORD]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]


def find_callsite(h, log):
    for base, size in S.regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                i = data.find(PATTERN)
                if i >= 0:
                    va = base + off + i
                    log('callsite pattern at 0x%08X' % va)
                    return va
            off += want
    return None


def build_stub(stub_va, buffer_va, original_va):
    """x86 shellcode: copy 16B from edx to buffer, flag, call original."""
    code = bytearray()
    code += b'\x60'                              # pushad
    code += b'\x89\xd6'                          # mov esi, edx
    code += b'\xbf' + struct.pack('<I', buffer_va)  # mov edi, buffer
    code += b'\xb9\x04\x00\x00\x00'              # mov ecx, 4
    code += b'\xf3\xa5'                          # rep movsd
    code += b'\xc7\x05' + struct.pack('<I', buffer_va + 16) + \
            b'\xef\xbe\xad\xde'                  # mov dword [buffer+16], flag
    code += b'\x61'                              # popad
    code += b'\xb8' + struct.pack('<I', original_va)  # mov eax, original
    code += b'\xff\xd0'                          # call eax
    code += b'\xc3'                              # ret
    return bytes(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--seconds', type=float, default=180.0)
    ap.add_argument('--reply-variant', type=int, default=3)
    ap.add_argument('--advertise-port', type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'key_capture.log'), 'w',
                encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    ok, err = S.enable_debug()
    log('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = S.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = S.PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % args.exe
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(args.exe, buf, None, None, True,
                              S.CREATE_SUSPENDED, None, args.cwd,
                              ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit('CreateProcess failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log('created suspended pid=%d' % pid)
    h = k32.OpenProcess(S.PROCESS_ALL_ACCESS, False, pid)
    log('handle=%s err=%d' % (h, ctypes.get_last_error()))
    if not h:
        k32.ResumeThread(pi.hThread)
        return 1

    # Start listeners and apply host redirects.
    stop = threading.Event()
    S.start_listeners(args.out, stop, args.reply_variant, '',
                      args.advertise_port)
    for base, size in S.regions(h):
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                for src, dst in S.REDIRECTS.items():
                    i = 0
                    while True:
                        i = data.find(src, i)
                        if i < 0:
                            break
                        S.write_bytes(h, base + off + i, dst)
                        i += 1
            off += want
    k32.ResumeThread(pi.hThread)
    log('resumed; waiting for ProtocalHandler callsite')

    callsite = None
    t0 = time.time()
    while time.time() - t0 < 30 and callsite is None:
        callsite = find_callsite(h, log)
        if callsite is None:
            time.sleep(0.5)
    if callsite is None:
        log('ProtocalHandler callsite not found')
        return 1

    base = callsite - CALLSITE_RVA
    call_va = base + CALL_RVA
    original_va = base + ORIGINAL_SETKEY_RVA
    log('ProtocalHandler base=0x%08X call=0x%08X original=0x%08X'
        % (base, call_va, original_va))

    alloc = k32.VirtualAllocEx(h, None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                               PAGE_EXECUTE_READWRITE)
    log('alloc=0x%08X' % (alloc or 0))
    if not alloc:
        return 1
    buffer_va = alloc
    stub_va = alloc + 0x100
    stub = build_stub(stub_va, buffer_va, original_va)
    written = ctypes.c_size_t()
    if not k32.WriteProcessMemory(h, ctypes.c_void_p(stub_va), stub,
                                  len(stub), ctypes.byref(written)):
        log('write stub failed err=%d' % ctypes.get_last_error())
        return 1
    zero = b'\x00' * 32
    k32.WriteProcessMemory(h, ctypes.c_void_p(buffer_va), zero, 32,
                           ctypes.byref(written))

    old = S.read_some(h, call_va, 5)
    log('original call bytes=%s' % old.hex())
    rel = stub_va - (call_va + 5)
    patch = b'\xe8' + struct.pack('<i', rel)

    # Briefly suspend all threads, patch, resume.
    st = ntdll.NtSuspendProcess(h)
    log('NtSuspendProcess=0x%X' % (st & 0xffffffff))
    okw = k32.WriteProcessMemory(h, ctypes.c_void_p(call_va), patch, 5,
                                 ctypes.byref(written))
    log('patch write=%s' % okw)
    st = ntdll.NtResumeProcess(h)
    log('NtResumeProcess=0x%X' % (st & 0xffffffff))

    cap = os.path.join(args.out, 'local_listeners.jsonl')
    found_key = None
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        raw = S.read_some(h, buffer_va, 20)
        if len(raw) == 20:
            flag = struct.unpack_from('<I', raw, 16)[0]
            if flag == 0xDEADBEEF:
                key = raw[:16]
                log('CAPTURED key=%s' % key.decode('ascii', 'replace'))
                found_key = key.decode('ascii', 'replace')
                # restore original call to reduce detection
                k32.WriteProcessMemory(h, ctypes.c_void_p(call_va), old, 5,
                                       ctypes.byref(written))
                log('restored original call bytes')
                break
        time.sleep(0.005)

    if found_key:
        with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump({'key': found_key, 'va': buffer_va}, fh, indent=2)
        log('KEY FOUND -> aes_key_FOUND.json')
    else:
        log('key not captured within %.0fs' % args.seconds)
    stop.set()
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
