# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

print("=== module/proc name strings relevant to networking ===")
for k in [b"ws2_32", b"WS2_32", b"wsock32", b"WSOCK32", b"mswsock", b"MSWSOCK",
          b"ws2help", b"WSAStartup", b"WSACleanup", b"gcloudvoice", b"GCloudVoice",
          b"GetProcAddress", b"LoadLibraryA", b"LoadLibraryW", b"LoadLibraryEx"]:
    hits = pe.find_cstr(k)
    print("  %-16s %d" % (k.decode(), len(hits)))
    for off, va in hits[:4]:
        if va is not None:
            print("        %08X" % va)

print()
print("=== hot indirect-call slots in the executable section (call dword ptr [imm32]) ===")
cnt = collections.Counter()
for o in range(len(d) - 6):
    if d[o] == 0xFF and d[o+1] == 0x15:
        tgt = struct.unpack_from("<I", d, o+2)[0]
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            cnt[tgt] += 1
for tgt, n in cnt.most_common(40):
    print("  [0x%08X] x%d" % (tgt, n))
