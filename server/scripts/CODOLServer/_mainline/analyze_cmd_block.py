"""命令名块里那些数字（3049/2942/3014...）是什么。

布局:
    0xDC6B00  "3049"
    0xDC6B08  "dw_room_partyInvitationTimeout"
    0xDC6B28  "2942"
    0xDC6B30  "2941"
    ...
    0xDC6B68  "room.create"
    ...

这些是**字符串形式的数字**（ASCII "3049"），不是 u32。
像是 localize 字符串 ID → 名字的映射表。

若命令注册用 ID，那注册表里存的应是 3049 这样的数字。
"""
import re
import struct

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
import pefile

pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\x00').decode('latin1'), base + s.VirtualAddress,
         s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
data = open(EXE, 'rb').read()


def va_of(o):
    for n, va, vs, pr, rs in secs:
        if pr <= o < pr + rs:
            return va + (o - pr)
    return None


# 这块的起止
lo = data.find(b'dw_room_partyInvitationTimeout') - 8
hi = data.find(b'party.promote') + 32
print('区块 0x%X .. 0x%X (%d 字节)' % (lo, hi, hi - lo))

# 把这块按 NUL 切分，标出"数字串"与"标识符"
chunk = data[lo:hi]
parts = chunk.split(b'\x00')
print()
print('=== 分项 ===')
nums = []
ids = []
for p in parts:
    p = p.strip()
    if not p:
        continue
    if re.fullmatch(rb'\d{3,6}', p):
        nums.append(int(p))
        print('  NUM  %s' % p.decode())
    elif re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_.]*', p):
        ids.append(p.decode())
        print('  NAME %s' % p.decode())
    else:
        print('  ?    %r' % p[:40])

print()
print('数字 %d 个: %s' % (len(nums), nums))
print('名字 %d 个: %s' % (len(ids), ids[:20]))

# 关键: 这些数字是否作为 u32 出现在别处（注册表用数字做 key）
print()
print('=== 数字 ID 作为 u32 的引用 ===')
for n in nums[:10]:
    needle = struct.pack('<I', n)
    cnt = data.count(needle)
    # 同时找 ASCII 形式的引用
    print('  %-6d u32 出现 %-4d 次  ASCII "%d" 出现 %d 次'
          % (n, cnt, n, data.count(str(n).encode())))
