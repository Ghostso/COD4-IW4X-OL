import struct, sys, os
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby3074"))

# Replicate what lsg_server.py builds
USER_NAME = "CODOL-LOCAL-0001"
CP_BALANCE = 985699
GP_BALANCE = 883599
PLAYER_ID = 11355988700816506746

def _profile_public():
    body = bytearray()
    body += struct.pack("<I", 0x2BC)            # result code 700
    body += USER_NAME.encode("ascii")
    body += b"\x00" * (0x40 - len(USER_NAME))
    body += struct.pack("<Q", PLAYER_ID)
    body += struct.pack("<I", CP_BALANCE)       # CP
    body += struct.pack("<I", GP_BALANCE)       # GP
    body += b"\x00" * 0x100
    return bytes(body)

def _profile_secure():
    body = bytearray()
    body += struct.pack("<I", 0x2BC)
    body += struct.pack("<Q", PLAYER_ID)
    body += struct.pack("<I", CP_BALANCE)
    body += struct.pack("<I", GP_BALANCE)
    body += b"\x00" * 0x200
    return bytes(body)

pub = _profile_public()
sec = _profile_secure()
print("public profile: %d bytes" % len(pub))
print("secure profile: %d bytes" % len(sec))
print()
print("=== 文档说三方实现里的档案大小 ===")
print("  8/1 public: 33428 bytes")
print("  8/2 secure: 32983 bytes")
print()
print("  我们: public=%d, secure=%d" % (len(pub), len(sec)))
print("  差了 33000+ 字节 — 里面应该有大量游戏数据（武器、装备、解锁等）")
print()
print("=== 对比：我们写了什么 ===")
print("  public: result_code(4) + username(0x40) + player_id(8) + CP(4) + GP(4) + zeros(0x100)")
print("  secure: result_code(4) + player_id(8) + CP(4) + GP(4) + zeros(0x200)")
print()
print("  这不是完整档案，只是一个骨架。")
print("  缺少：武器列表、解锁状态、等级、经验值、角色外观、附件、连杀奖励等")
print("  客户端可能需要这些数据来渲染大厅界面")
