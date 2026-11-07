# -*- coding: utf-8 -*-
"""用现有 codol_crypto 代码，离线复算 21/5 应答的 306 字节布局（不发送、不联网）。"""
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT')
import codol_crypto as cc

# 会话对象（本次用日志中记录的参数重建，仅用于"布局算术"验证，不作为原始响应）
obj = cc.build_mission_session_object(False, playlist=10,
        map_override='coop_take_mp_fav_tropical', game_type_override=0x1000003)
print("session object len = %d (日志记 236)" % len(obj))

# inner 结构（不含对象负载）
reply_id = 47; task = 5; status = 0
inner = bytearray()
inner += bytes([10]) + struct.pack("<Q", reply_id)
inner += bytes([8]) + struct.pack("<I", status)
inner += bytes([3, task & 0xFF])
inner += bytes([8]) + struct.pack("<I", 1)      # len(objects)=1
inner += bytes([8]) + struct.pack("<I", 1)
inner += obj
print("inner len = %d" % len(inner))
n = (5 + len(inner) + 15) // 16 * 16
print("padded plain len = %d  (5+inner+pad)" % n)
frame = 26 + n + 8
print("frame len = 26 + %d + 8 = %d   <- 对照日志: (306 字节)" % (n, frame))
print()
print("=== 逐字段 ===")
print("  [0:4]   len-4      = 0x%08X (%d)" % (frame-4, frame-4))
print("  [4]     MARK        = 0x85")
print("  [5]     KIND_TASK   = 0x01? (cc.KIND_TASK=0x%02X)" % cc.KIND_TASK)
print("  [6:10]  seq_out     = %d" % reply_id)
print("  [10:26] IV (16B, os.urandom -> 每帧不同)")
print("  [26:%d] ciphertext (AES-CBC, %dB)" % (26+n, n))
print("  [%d:%d] hmac8" % (26+n, frame))
print()
print("=== 明文（解密后）布局 ===")
print("  [0:4]   inner 长度 = %d" % len(inner))
print("  [4]     marker = 1 (应答)")
print("  [5:5+%d] inner" % len(inner))
print()
print("=== inner 内部 ===")
off = 0
print("  +0x00  0x0A <reply_id u64>      ; replyId = %d" % reply_id)
print("  +0x09  0x08 <status u32>        ; status = %d" % status)
print("  +0x0E  0x03 <task u8>           ; task = %d" % task)
print("  +0x10  0x08 <len(objects) u32>  ; = 1")
print("  +0x15  0x08 <len(objects) u32>  ; = 1 (重复)")
print("  +0x1A  <session object %d B>" % len(obj))
print()
print("=== 会话对象内部结构（build_mission_session_object 的字段序）===")
for i, l in enumerate(cc.build_mission_session_object.__doc__.split('\n') if cc.build_mission_session_object.__doc__ else []):
    if l.strip(): print("   " + l.strip())
