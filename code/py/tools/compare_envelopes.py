"""对比两种推送信封的字节形态, 判断哪个与客户端上行一致。

用法: python -I tools/compare_envelopes.py <kit_dir>
"""
import importlib.util
import os
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else r'run_codol_001\kit_roommsg_20261028'
sys.path.insert(0, os.path.abspath(KIT))

spec = importlib.util.spec_from_file_location(
    'lobby_under_test', os.path.join(KIT, 'lobby_server.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import codol_crypto as cc

payload = mod.build_roominfo_payload(mod.ROOM_ID, room_name=b'BOTMatch')

a = mod.build_room_push(1, 'HostUser', mod.ROOM_ID, payload)
b = cc.instant_push_body(1, 'HostUser', payload, kind=11, use_types=True)
c = cc.instant_push_body(0, 'Server', payload, kind=11, use_types=False)

print('内层 payload  (RoomInfo, %d B): %s' % (len(payload), payload.hex()))
print()
print('A build_room_push      (%3d B): %s' % (len(a), a.hex()))
print('B instant_push_body T  (%3d B): %s' % (len(b), b.hex()))
print('C instant_push_body -T (%3d B): %s' % (len(c), c.hex()))
print()
print('客户端上行 11/4 批次样本 (245B):')
print('  10000000020200000018000000d0...  <- 以 u32 长度开头, 无 08/0A/10/13 tag')
