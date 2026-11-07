"""找 dwRoomMatch::Init 的函数体。

符号名 ??Init@dwRoomMatch@@SAXXZ@ 在 .rdata（调试/导出信息）。
函数体是普通代码，不含该符号。

方法: 用 MyEventHandler 的 RTTI 名地址（0xE6EFE4）在代码段搜引用。
函数局部类的 vtable 赋值通常写成 mov dword [esp+X], offset <vtable>
而 vtable 的 COL 指向 TD。TD 引用为 0 说明连 COL 都没生成 ——
那就直接搜 RTTI 名地址本身的引用。
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

CODE = [s for s in secs if s[0] == '.tp3'][0]
print('代码节 .tp3 VA=0x%08X size=0x%X pr=0x%X rs=0x%X' % (CODE[1], CODE[2], CODE[3], CODE[4]))


def va_of(o):
    for n, va, vs, pr, rs in secs:
        if pr <= o < pr + rs:
            return va + (o - pr)
    return None


md = Cs(CS_ARCH_X86, CS_MODE_32)

NAME_VA = 0x00E6EFE4
TD_VA = 0x00E6EFDB

for label, target in (('RTTI 名', NAME_VA), ('TD', TD_VA)):
    needle = struct.pack('<I', target)
    hits = []
    i = data.find(needle)
    while i >= 0 and len(hits) < 30:
        hits.append(i)
        i = data.find(needle, i + 1)
    print()
    print('=== 引用 %s (0x%08X): %d 处 ===' % (label, target, len(hits)))
    for h in hits[:8]:
        va = va_of(h)
        ctx = data[max(0, h - 20):h + 12]
        print('  文件 0x%-8X VA 0x%08X  ctx=%s' % (h, va, ctx.hex()))

# 直接用名字串本身找：字符 'M','y'... 附近
print()
print('=== MyEventHandler 名字附近 0x40 字节 ===')
o = data.find(b'.?AVMyEventHandler@')
print(data[o - 16:o + 64].hex())
