#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codol_launch.py -- offline launcher prototype for CODOL (codoMP_client_shipRetail.exe).

Replicates, from static analysis of TCLS.dll, the hand-off TCLS performs around
CreateProcessW of the game:

  1. wide command line template (TCLS.dll 0x103C53CC):
         "<game exe>" -q <uId> -i <d1> -s <d2> -g <d3> -u <u2> -n <name> [ -m --1 ]
     (TCLS.dll 0x103C53BC appends " -m --1" when the tcls daemon channel flag is not set)
  2. CreateProcessW(exe, cmdline, NULL, NULL, inherit=TRUE, flags, NULL, cwd, si, pi)
     -- TCLS.dll 0x10044AE4 (flags=0, non-suspended)
  3. shared memories named after the *created* pid (TCLS.dll 0x1003FD10 / 0x1003F500):
         TCLS_TASMEMORY_<pid>    size 0x7AC, payload encrypted (see tas_crypt.py)
         TCLS_SHELLMEMORY_<pid>  size 0x224, plaintext
     The game's TenProtect opens them by its own pid; the TAS block is decrypted with
     the file-time of the game exe as key (TCLS.dll 0x100D7BF0 GetFileTime).

Usage (from the "COD OL" directory):
    python scripts\\codol_launch.py --mode baseline
    python scripts\\codol_launch.py --mode full -q 12345 --keep 30
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tas_crypt import encrypt, DEFAULT_KEY  # noqa: E402

# Reader side actually opened by the game (observed via Frida OpenFileMappingW):
#   TCLS_SHAREDMEMEMORY<pid>          (no underscore, note the MEMEMORY typo)
# The TCLS writer side uses these two names instead:
#   TCLS_TASMEMORY_<pid> / TCLS_SHELLMEMORY_<pid>
SHARED_NAME_FMT = 'TCLS_SHAREDMEMEMORY%d'
TAS_NAME_FMT = 'TCLS_TASMEMORY_%d'
SHELL_NAME_FMT = 'TCLS_SHELLMEMORY_%d'

TAS_SIZE = 0x7AC
TAS_ENC_OFFSET = 4
TAS_ENC_LEN = TAS_SIZE - TAS_ENC_OFFSET      # 0x7A8, pushed at TCLS 0x100401DC

SHELL_SIZE = 0x224

CREATE_SUSPENDED = 0x00000004
PAGE_READWRITE = 0x04
FILE_MAP_ALL_ACCESS = 0x000F001F
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

k32 = ctypes.WinDLL('kernel32', use_last_error=True)


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
                ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
                ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
                ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', wt.HANDLE),
                ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


def _setup_prototypes():
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD, ctypes.c_size_t]
    k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.argtypes = [wt.HANDLE]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k32.CreateProcessW.restype = wt.BOOL
    k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                   wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                                   ctypes.c_void_p, ctypes.c_void_p]


_setup_prototypes()


def filetime_key(path):
    """TCLS 0x100D7BF0: GetFileTime(hFile, NULL, NULL, &ftLastWrite) -> 8 key bytes."""
    try:
        st = os.stat(path)
    except OSError:
        return DEFAULT_KEY
    ft = int(st.st_mtime * 10000000) + 116444736000000000
    lo, hi = ft & 0xFFFFFFFF, (ft >> 32) & 0xFFFFFFFF
    if lo == 0 and hi == 0:
        return DEFAULT_KEY
    return struct.pack('<II', lo, hi)


def build_tas_payload(key, len1=0, block1=b'', len2=0, block2=b'',
                      field490=0, field494=0, text_utf8=b''):
    """Mirror of TCLS 0x1003FD10."""
    buf = bytearray(TAS_SIZE)
    struct.pack_into('<I', buf, 0x004, TAS_SIZE)
    block1 = bytes(block1)[:0x400]
    block2 = bytes(block2)[:0x80]
    struct.pack_into('<I', buf, 0x008, len1 or len(block1))
    struct.pack_into('<I', buf, 0x00C, len2 or len(block2))
    buf[0x010:0x010 + len(block1)] = block1
    buf[0x410:0x410 + len(block2)] = block2
    struct.pack_into('<I', buf, 0x490, field490)
    struct.pack_into('<I', buf, 0x494, field494)
    t = bytes(text_utf8)[:0x104]
    buf[0x498:0x498 + len(t)] = t
    struct.pack_into('<I', buf, 0x000, 0)                        # not ready
    buf[TAS_ENC_OFFSET:TAS_ENC_OFFSET + TAS_ENC_LEN] = encrypt(  # TCLS 0x100401FF
        key, bytes(buf[TAS_ENC_OFFSET:TAS_ENC_OFFSET + TAS_ENC_LEN]))
    struct.pack_into('<I', buf, 0x000, 1)                        # ready
    return bytes(buf)


def build_shell_payload(field8=0, fieldC=0):
    """Mirror of TCLS 0x1003F500 (plaintext, size 0x224)."""
    buf = bytearray(SHELL_SIZE)
    struct.pack_into('<I', buf, 0x004, SHELL_SIZE)
    struct.pack_into('<I', buf, 0x008, field8)
    struct.pack_into('<I', buf, 0x00C, fieldC)
    struct.pack_into('<I', buf, 0x010, 1)
    return bytes(buf)


def build_safe_shared_payload(ready=0):
    """
    Minimal TCLS_SHAREDMEMEMORY<pid> payload that the client accepts without
    crashing.

    Reverse-engineering result (2026-09-25, Frida crash probe):
      - the reader dereferences the dword at block+0x054 as a pointer/offset;
        a random value there produces an access-violation (0xC0000005),
        zero is safe;
      - a fully zero 0x7AC block (with size at +0x004) survives and lets the
        client continue running.

    So we deliberately leave block1/block2 zeroed instead of inventing TAS
    login data. This is enough to keep the client alive for network probing.
    """
    buf = bytearray(TAS_SIZE)
    struct.pack_into('<I', buf, 0x004, TAS_SIZE)   # size field
    struct.pack_into('<I', buf, 0x000, ready)      # ready flag
    return bytes(buf)


def create_mapping(name, payload):
    h = k32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, PAGE_READWRITE,
                               0, len(payload), name)
    if not h:
        raise OSError('CreateFileMappingW(%s) failed: %d' %
                      (name, ctypes.get_last_error()))
    p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, len(payload))
    if not p:
        k32.CloseHandle(h)
        raise OSError('MapViewOfFile(%s) failed: %d' % (name, ctypes.get_last_error()))
    ctypes.memmove(p, payload, len(payload))
    k32.UnmapViewOfFile(p)
    return h


def find_game(root):
    for cand in ('codoMP_client_shipRetail.exe',
                 os.path.join('bin', 'codoMP_client_shipRetail.exe')):
        p = os.path.join(root, cand)
        if os.path.isfile(p):
            return p
    raise SystemExit('game exe not found under %s' % root)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.abspath(os.path.join(here, '..')),
                    help='the "COD OL" directory')
    ap.add_argument('--mode', choices=('baseline', 'full'), default='full')
    ap.add_argument('-q', '--uid', default='0', help='uid for -q (template arg 1)')
    ap.add_argument('-i', dest='d1', default='0')
    ap.add_argument('-s', dest='d2', default='0')
    ap.add_argument('-g', dest='d3', default='0')
    ap.add_argument('-u', dest='u2', default='0')
    ap.add_argument('-n', dest='name', default='')
    ap.add_argument('--extra', default='-m --1', help='verbatim tail (empty string omits)')
    ap.add_argument('--keep', type=float, default=20.0, help='seconds to watch after launch')
    ap.add_argument('--no-shm', action='store_true')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    exe = find_game(root)
    key = filetime_key(exe)
    print('[i] exe     : %s' % exe)
    print('[i] key(ft) : %s' % key.hex())

    if args.mode == 'baseline':
        cmdline = '"%s" -q' % exe
    else:
        cmdline = '"%s" -q %s -i %s -s %s -g %s -u %s -n %s' % (
            exe, args.uid, args.d1, args.d2, args.d3, args.u2, args.name)
        if args.extra:
            cmdline += ' ' + args.extra
    print('[i] cmdline : %s' % cmdline)
    print('[i] cwd     : %s' % root)

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    buf = ctypes.create_unicode_buffer(cmdline)

    ok = k32.CreateProcessW(exe, buf, None, None, True, CREATE_SUSPENDED,
                            None, root, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise SystemExit('CreateProcessW failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    print('[+] created pid=%d (suspended)' % pid)

    handles = []
    if not args.no_shm:
        tas_payload = build_tas_payload(key, text_utf8=args.name.encode('utf-8'))
        shell_payload = build_shell_payload()
        for name, payload in ((SHARED_NAME_FMT % pid, tas_payload),
                              (TAS_NAME_FMT % pid, tas_payload),
                              (SHELL_NAME_FMT % pid, shell_payload)):
            try:
                handles.append(create_mapping(name, payload))
                print('[+] mapping %-30s %d bytes' % (name, len(payload)))
            except OSError as e:
                print('[!] %s' % e)

    k32.ResumeThread(pi.hThread)
    print('[+] resumed')

    deadline = time.time() + args.keep
    exitcode = None
    while time.time() < deadline:
        if k32.WaitForSingleObject(pi.hProcess, 250) == 0:
            code = wt.DWORD()
            k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            exitcode = code.value
            break
    if exitcode is None:
        print('[i] still running after %.0fs' % args.keep)
    else:
        print('[i] exited, code=0x%08X (%d)' % (exitcode, exitcode))
    for h in handles:
        k32.CloseHandle(h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
