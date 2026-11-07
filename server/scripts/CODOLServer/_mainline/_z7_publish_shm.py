# -*- coding: utf-8 -*-
"""Publish TCLS_SHAREDMEMEMORY<pid> for the running game process.

Usage:
    python _z7_publish_shm.py <pid> [image_path]

The 0x80000-byte image must contain a valid slot table so TenProxy.dll
ApplySettings succeeds and [0x331C5C0] flips to 1, which un-gates the lobby
UI stage (objC creation).
"""
import ctypes, ctypes.wintypes as wt, os, sys, time

INVALID_HANDLE_VALUE = wt.HANDLE(-1).value
FILE_MAP_ALL_ACCESS = 0xF001F
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

def publish_shm(pid, image_path):
    blob = open(image_path, "rb").read()
    k32.CreateFileMappingW.restype = wt.HANDLE
    k32.CreateFileMappingW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                                       wt.DWORD, wt.DWORD, wt.LPCWSTR]
    k32.MapViewOfFile.restype = ctypes.c_void_p
    k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD,
                                  ctypes.c_size_t]
    k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    name = "TCLS_SHAREDMEMEMORY%d" % pid
    h = k32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, 0x04, 0,
                               len(blob), name)
    if not h:
        return None, "CreateFileMappingW err=%d" % ctypes.get_last_error()
    p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, len(blob))
    if not p:
        err = ctypes.get_last_error()
        k32.CloseHandle(h)
        return None, "MapViewOfFile err=%d" % err
    ctypes.memmove(p, blob, len(blob))
    k32.UnmapViewOfFile(p)
    # Keep the handle open: it is the only reference keeping the mapping alive.
    return h, "ok size=%d" % len(blob)

if __name__ == "__main__":
    pid = int(sys.argv[1])
    img = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(__file__), "..", "_subagents", "_tenproxy_shm.bin")
    img = os.path.abspath(img)
    h, msg = publish_shm(pid, img)
    print("pid=%d image=%s result=%s handle=%s" % (pid, img, msg, h))
    if h:
        # Keep alive for 200 seconds (long enough for a 150 s run).
        time.sleep(200)
