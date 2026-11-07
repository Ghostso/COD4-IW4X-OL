"""确认房间推送信封里两个路由 dword 的来源。

0x7E7C90 的路由键:
    entry+0x10 == 第 1 个 dword 参数
    entry+0x14 == 第 2 个 dword 参数
建房后实测: 0x55667788 / 0x11223344  (= roomId 0x1122334455667788 的高/低 32 位)

本脚本:
  1. 打印我们两种信封各字段的字节位置
  2. 指出哪些字段会成为 (dword, dword) 路由键
用法: python -I tools/check_route_key.py <kit_dir>
"""
import importlib.util
import os
import struct
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else r'run_codol_001\kit_roommsg_20261028'
sys.path.insert(0, os.path.abspath(KIT))
spec = importlib.util.spec_from_file_location(
    'lb', os.path.join(KIT, 'lobby_server.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import codol_crypto as cc

ROOM = mod.ROOM_ID
print('ROOM_ID = 0x%016X' % ROOM)
print('  低32 = 0x%08X   高32 = 0x%08X' % (ROOM & 0xFFFFFFFF, ROOM >> 32))
print('  实测表项 service=0x%08X task=0x%08X  (= 高32 / 低32)'
      % (ROOM >> 32, ROOM & 0xFFFFFFFF))
print()

payload = mod.build_roominfo_payload(ROOM, room_name=b'BOTMatch')

for label, body in (
        ('A build_room_push', mod.build_room_push(1, 'HostUser', ROOM, payload)),
        ('B instant_push k11', cc.instant_push_body(1, 'HostUser', payload, kind=11)),
):
    print('%s  (%d B)' % (label, len(body)))
    print('  hex: %s' % body.hex())
    # 扫描 body 里所有出现 roomId(或其拆分)的位置
    lo, hi = struct.pack('<I', ROOM & 0xFFFFFFFF), struct.pack('<I', ROOM >> 32)
    full = struct.pack('<Q', ROOM)
    for name, needle in (('roomId(u64 LE)', full), ('roomId_lo', lo), ('roomId_hi', hi)):
        i = body.find(needle)
        print('  %-14s at offset %s' % (name, i if i >= 0 else '不在'))
    print()
