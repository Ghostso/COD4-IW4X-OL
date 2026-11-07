"""确认 dwRoomMatch::Init 是否属于"启动期一次性初始化"。

方法: 看它和同组的其他 Init 是否被同一处代码批量调用。
7 个 UiCpp*View::Init + dwRoomMatch::Init 都是 `static void`。

若有统一的"注册所有 View"的代码，会在同一函数里连续调用它们。
搜: 每个 Init 的地址，找它们在代码里的 **相对偏移模式**。
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


# 找这些类的 Init 函数体。
# 线索: MyEventHandler 的 vtable 在 0xDC78E8，其 COL 在 0xDF869C。
# Init 函数体会引用该 vtable 或使用其附近的栈对象。
# 先找 vtable 附近还有什么 vtable（同族类）
print('=== 0xDC78E8 附近 0x80 字节 ===')
o = None
for n, sva, vs, pr, rs in secs:
    if sva <= 0x00DC78E8 < sva + vs:
        o = pr + (0x00DC78E8 - sva)
        break
if o:
    d = data[o - 0x20:o + 0x60]
    for i in range(0, len(d), 16):
        vals = ' '.join('%08X' % struct.unpack_from('<I', d, i + k)[0]
                        for k in range(0, 16, 4))
        print('  0x%08X  %s' % (0x00DC78E8 - 0x20 + i, vals))

print()
print('=== 找引用 0xDC78E8 的代码（vtable 赋值的常见写法）===')
# mov dword ptr [reg], imm32  ->  C7 00 E8 78 DC 00 等
pats = [
    b'\xc7\x00' + struct.pack('<I', 0x00DC78E8),
    b'\xc7\x01' + struct.pack('<I', 0x00DC78E8),
    b'\xc7\x02' + struct.pack('<I', 0x00DC78E8),
    b'\xc7\x03' + struct.pack('<I', 0x00DC78E8),
    b'\xc7\x06' + struct.pack('<I', 0x00DC78E8),
    b'\xc7\x07' + struct.pack('<I', 0x00DC78E8),
    b'\x68' + struct.pack('<I', 0x00DC78E8),
]
total = 0
for p in pats:
    i = data.find(p)
    while i >= 0:
        print('  %s  @ VA 0x%08X' % (p[:2].hex(), va_of(i)))
        total += 1
        i = data.find(p, i + 1)
print('  共 %d 处' % total)

# 也许 vtable 是通过 lea/mov 寄存器传入的，搜"vtable 附近任一地址"出现在代码里
print()
print('=== MyEventHandler COL (0xDF869C) 被引用处 ===')
needle = struct.pack('<I', 0x00DF869C)
i = data.find(needle)
cnt = 0
while i >= 0:
    print('  VA 0x%08X  ctx=%s' % (va_of(i), data[max(0, i - 12):i + 12].hex()))
    cnt += 1
    i = data.find(needle, i + 1)
print('  共 %d 处' % cnt)
