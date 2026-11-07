"""确认 0x82E151C..0x82E1540 这批 handler 是不是"静态构造"的。

若它们在 .data 里有初值（文件里就存在），说明启动即建好。
那 MyEventHandler（0xDC78E8）为什么不在其中？

对比:
    handler[i] 的 vtable 都在 0xDC6Dxx / 0xDC6Exx
    MyEventHandler 的 vtable 是 0xDC78E8 —— 不在这批里
"""
import struct
import pefile

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\x00').decode('latin1'), base + s.VirtualAddress,
         s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
data = open(EXE, 'rb').read()


def off_of(va):
    for n, sva, vs, pr, rs in secs:
        if sva <= va < sva + vs:
            o = pr + (va - sva)
            if o < len(data):
                return o
    return None


print('=== 0x82E151C 在文件里有初值吗 ===')
for va in (0x082E151C, 0x082E1520, 0x082E1540, 0x082E1450):
    o = off_of(va)
    if o is None:
        print('  0x%08X 不在文件里（.bss 运行期填充）' % va)
    else:
        v = struct.unpack_from('<I', data, o)[0]
        print('  0x%08X 文件偏移 0x%X 值=0x%08X' % (va, o, v))

print()
print('=== 这些 vtable 存在吗 ===')
for vt in (0x00DC6DD8, 0x00DC6DE0, 0x00DC78E8):
    o = off_of(vt)
    if o is None:
        print('  vtable 0x%08X 不在文件' % vt)
        continue
    vals = struct.unpack_from('<6I', data, o)
    print('  vtable 0x%08X slots=%s' % (vt, [hex(x) for x in vals]))

print()
print('=== 0xDC6DD8 与 0xDC78E8 的关系 ===')
print('  0xDC6DD8 属于 0x82E151C 那批 handler 表')
print('  0xDC78E8 是 MyEventHandler 的 vtable')
print('  两者相隔 0x%X 字节' % (0x00DC78E8 - 0x00DC6DD8))
