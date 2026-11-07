"""查 room.* 命令名的引用方式。

之前用"绝对地址 dword 引用"搜到 0，但这可能是因为:
    - 命令表用 (name_ptr, flag, handler) 结构但没对齐
    - 或名字被拼接后注册

换个搜法: 在同一 .rdata 区域里看这些名字**周围**是什么，
         若是命令结构体数组，会有规律的 handler 指针。
"""
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


def off_of(va):
    for n, sva, vs, pr, rs in secs:
        if sva <= va < sva + vs:
            return pr + (va - sva)
    return None


# 1) 这些名字所在区段
print('=== room.* 命令名所在区段 ===')
for nm in (b'room.startgame', b'room.changemap', b'room.create',
           b'room.list', b'room.match.quick'):
    off = data.find(nm)
    if off < 0:
        continue
    va = va_of(off)
    for n, sva, vs, pr, rs in secs:
        if pr <= off < pr + rs:
            print('  %-20s off=0x%X va=0x%08X 节=%s' % (nm.decode(), off, va, n))
            break

# 2) 看这附近的字符串布局（判断是不是命令名字符串块）
print()
print('=== 0x6B2B00 附近的可打印串 ===')
start = 0x6B2B00
chunk = data[start:start + 0x180]
cur, cs = bytearray(), None
for i, c in enumerate(chunk):
    if 32 <= c < 127:
        if cs is None:
            cs = i
        cur.append(c)
    else:
        if len(cur) >= 4:
            print('  0x%08X  %s' % (va_of(start + cs), cur.decode()))
        cur, cs = bytearray(), None

# 3) 找"字符串地址表": 连续的 dword，每个都指向一个 room.* 串
print()
print('=== 搜连续的 room.* 地址表 ===')
addrs = {}
for nm in (b'room.create', b'room.join', b'room.leave', b'room.list',
           b'room.startgame', b'room.changemap', b'room.changeteam',
           b'room.members', b'room.say', b'room.servers'):
    o = data.find(nm)
    if o >= 0:
        addrs[nm.decode()] = va_of(o)
print('  名字 VA:', {k: hex(v) for k, v in addrs.items()})

for name, va in addrs.items():
    needle = struct.pack('<I', va)
    hits = []
    i = data.find(needle)
    while i >= 0 and len(hits) < 5:
        hits.append(i)
        i = data.find(needle, i + 1)
    if hits:
        print('  %-18s 被引用 %d 次 at %s' % (name, len(hits), [hex(h) for h in hits]))
