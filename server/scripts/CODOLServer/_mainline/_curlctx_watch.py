"""Deep-field sampler: objB -> httpobj -> curl ctx, read status lineage.

Extends _bdfield_watch.py.  Static evidence (image_best.bin, VA-based):
  [httpobj+0x464]  <- poll copies propid 0x200002 result here (0xC752DD)
  propid 0x200002  -> [ctx+0x870C]   (0xAD471D via 0xAD4700/0xAD4A70/0xAC95F0)
  writers of ctx+0x870C (httpcode):  0xAD45BC (init 0),
                                     0xAD8AE9 (force 0x130 / "Simulate 304"),
                                     0xADE3C1 (RTSP path copy), 0xAE7521 (cond)
  writer of ctx+0x8710 (sscanf "HTTP/1.%d %d" status): 0xAEDC15

So at failure time:
  8710==200 && 870C==0  ->  parsed but not copied (header-complete never ran)
  8710==0   && 870C==0  ->  response bytes never reached the header parser
  8710==100             ->  interim 100 stuck (Expect handling)

READ-ONLY.  ASCII only.  Admin + SeDebug not required for own child process
(spawned CREATE_SUSPENDED by this script), but run elevated anyway.

Usage:
  python -X utf8 _curlctx_watch.py --cwd <sandbox> --out <dir> \
      --seconds 90 --step 0.25
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)

OBJB = 0x84ABB14
DW = 0x84ABA50
SUB = 0x84ABA60
ERR = 0x84ABA5C


class LUID(ctypes.Structure):
    _fields_ = [("L", wt.DWORD), ("H", wt.LONG)]


class LAA(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attr", wt.DWORD)]


class TP(ctypes.Structure):
    _fields_ = [("n", wt.DWORD), ("p", LAA * 1)]


class SI(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("r", wt.LPWSTR), ("d", wt.LPWSTR),
                ("t", wt.LPWSTR), ("x", wt.DWORD), ("y", wt.DWORD),
                ("xs", wt.DWORD), ("ys", wt.DWORD), ("xc", wt.DWORD),
                ("yc", wt.DWORD), ("fa", wt.DWORD), ("fl", wt.DWORD),
                ("sw", wt.WORD), ("cr", wt.WORD), ("rp", ctypes.c_void_p),
                ("hi", wt.HANDLE), ("ho", wt.HANDLE), ("he", wt.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [("hp", wt.HANDLE), ("ht", wt.HANDLE),
                ("pid", wt.DWORD), ("tid", wt.DWORD)]


def setup():
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD,
                                     ctypes.POINTER(ctypes.c_void_p)]
    adv.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                          ctypes.POINTER(LUID)]
    adv.AdjustTokenPrivileges.argtypes = [ctypes.c_void_p, wt.BOOL,
                                          ctypes.POINTER(TP), wt.DWORD,
                                          ctypes.c_void_p,
                                          ctypes.POINTER(wt.DWORD)]
    h = ctypes.c_void_p()
    adv.OpenProcessToken(k32.GetCurrentProcess(), 0x28, ctypes.byref(h))
    lu = LUID()
    adv.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(lu))
    tp = TP()
    tp.n = 1
    tp.p[0].Luid = lu
    tp.p[0].Attr = 2
    adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
    k32.CreateProcessW.restype = wt.BOOL
    k32.CreateProcessW.argtypes = [
        wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL,
        wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(SI),
        ctypes.POINTER(PI)]
    k32.OpenProcess.restype = wt.HANDLE
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.ReadProcessMemory.restype = wt.BOOL
    k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]
    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def rd(h, va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value] if got.value else None


def d32(h, va):
    b = rd(h, va, 4)
    return struct.unpack("<I", b)[0] if b and len(b) == 4 else None
