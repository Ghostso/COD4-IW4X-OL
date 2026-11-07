"""MyEventHandler vtable = 0xDC78E8 找到了。
现在找谁构造它（即 dwRoomMatch::Init 的调用点）。

构造过程: 对象内存里写入 vtable 地址。
搜 `mov dword [reg], 0xDC78E8` 或 `push 0xDC78E8`。
"""
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
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


VT = 0x00DC78E8
md = Cs(CS_ARCH_X86, CS_MODE_32)

# vtable 地址作为立即数出现的所有位置
needle = struct.pack('<I', VT)
hits = []
i = data.find(needle)
while i >= 0:
    hits.append(i)
    i = data.find(needle, i + 1)

print('vtable 0x%08X 出现 %d 处' % (VT, len(hits)))
for h in hits:
    va = va_of(h)
    ctx = data[max(0, h - 24):h + 20]
    print('  文件 0x%-8X VA 0x%08X  %s' % (h, va, ctx.hex()))

print()
print('=== 0x63B500（建房回调）被引用处 ===')
needle = struct.pack('<I', 0x0063B500)
cnt = data.count(needle)
print('  作为 dword 出现 %d 次' % cnt)
i = data.find(needle)
while i >= 0:
    print('    文件 0x%-8X VA 0x%08X  ctx=%s'
          % (i, va_of(i), data[max(0, i - 12):i + 12].hex()))
    i = data.find(needle, i + 1)

# 直接 call 0x63B500 的指令
print()
print('=== call 0x63B500 的调用点 ===')
hits = []
for i in range(len(data) - 5):
    if data[i] != 0xE8:
        continue
    rel = struct.unpack_from('<i', data, i + 1)[0]
    if va_of(i) is None:
        continue
    if (va_of(i) + 5 + rel) & 0xFFFFFFFF == 0x0063B500:
        hits.append(i)
print('  直接 call: %d 处 %s' % (len(hits), [hex(va_of(h)) for h in hits[:10]]))
