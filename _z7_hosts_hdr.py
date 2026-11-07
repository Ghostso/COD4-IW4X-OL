# -*- coding: utf-8 -*-
"""Restore the standard hosts comment header + keep the two redirect lines."""
import json, os, socket
STAGE = r"D:\z7tmp"
helper = r'''
import ctypes, os
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ=0x80000000; GENERIC_WRITE=0x40000000
OPEN_EXISTING=3; FILE_ATTRIBUTE_NORMAL=0x80
H = os.path.join(os.environ["windir"], "System32", "drivers", "etc", "hosts")

HEADER = """# Copyright (c) 1993-2009 Microsoft Corp.
#
# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.
#
# This file contains the mappings of IP addresses to host names. Each
# entry should be kept on an individual line. The IP address should
# be placed in the first column followed by the corresponding host name.
# The IP address and the host name should be separated by at least one
# space.
#
# Additionally, comments (such as these) may be inserted on individual
# lines or following the machine name denoted by a # symbol.
#
# For example:
#
#      102.54.94.97     rhino.acme.com          # source server
#       38.25.63.10     x.acme.com              # x client host

# localhost name resolution is handled within DNS itself.
#\t127.0.0.1       localhost
#\t::1             localhost

# z7 codol local lobby
127.0.0.1 formal-zone-auth.codol.qq.com
127.0.0.2 formal-zone-lsg.codol.qq.com
"""
new = HEADER.replace("\n", "\r\n").encode("utf-8")

k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                            wintypes.HANDLE]
k32.WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
k32.SetFilePointer.argtypes = [wintypes.HANDLE, wintypes.LONG, wintypes.LPVOID, wintypes.DWORD]
k32.SetEndOfFile.argtypes = [wintypes.HANDLE]

h = k32.CreateFileW(H, GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL, None)
k32.SetFilePointer(h, 0, None, 0)
w = wintypes.DWORD()
k32.WriteFile(h, new, len(new), ctypes.byref(w), None)
k32.SetEndOfFile(h)
k32.CloseHandle(h)
print("wrote", w.value, "bytes")
print("size now:", os.path.getsize(H))
'''
hp = os.path.join(STAGE, "hosts_hdr.py")
open(hp,"wb").write(helper.replace("\n","\r\n").encode("ascii"))
st = json.load(open(os.path.join("CODOLServer","logs","elevated_agent.json"), encoding="utf-8"))
req = {"action":"run","argv":["python","-X","utf8",hp],"token":st["token"]}
s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=600)
s.sendall((json.dumps(req)+"\n").encode("utf-8"))
buf=b""
while not buf.endswith(b"\n"):
    c=s.recv(65536)
    if not c: break
    buf+=c
r=json.loads(buf.decode("utf-8"))
print("rc:",r.get("rc"))
print(r.get("stdout"))
print((r.get("stderr") or "")[:400])
