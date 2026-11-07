# -*- coding: utf-8 -*-
"""Demonstrate the status field of the 0x85 task reply for a purchase failure.

build_task_reply_objects() writes `status` as a varint field #2.  The dispatch
site in lobby_server.py passes a literal 0, so a failed purchase and a
successful one are byte-identical: only the object list differs, and for a
purchase both are empty.
"""
import sys, os, struct, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

GOLDEN = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
sys.path.insert(0, GOLDEN)
import codol_crypto as cc

print('build_task_reply_objects(aes, hmac, seq, task, reply_id, objects, status)')
print('  inner layout:')
print('    field 1 (0x0A u64) = reply_id')
print('    field 2 (0x08 u32) = status      <-- only signal of success/failure')
print('    field 3 (0x03 u8)  = task')
print('    field 4 (0x08 u32) = len(objects)')
print()

for status in (0, 1):
    inner = bytearray()
    inner += bytes([10]) + struct.pack('<Q', 123)
    inner += bytes([8]) + struct.pack('<I', status)
    inner += bytes([3, 131 & 0xFF])
    inner += bytes([8]) + struct.pack('<I', 0)
    print('status=%d -> inner hex: %s' % (status, inner.hex(' ')))

print()
print('lobby_server.py dispatch (line ~1162):')
p = os.path.join(GOLDEN, 'lobby_server.py')
for i, line in enumerate(open(p, encoding='utf-8'), 1):
    if 1158 <= i <= 1166:
        print('  %4d %s' % (i, line.rstrip()))
