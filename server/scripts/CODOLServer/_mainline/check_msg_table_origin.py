"""确认 0x82E1458 表是静态初始化还是运行期填充, 并把 0x31..0x48 的处理器身份解出来。

两种可能:
  A. 表内容静态(在 .data 里初始化)  -> 我们该用 0x31..0x48
  B. 表运行期按房间状态填充          -> 0x03..0x2D 才是对的, 只是当时未填

判别方法: 找到表所在的 PE 节, 看该地址在**文件**里有没有初值(而非仅内存)。
同时反汇编 0x0810D978 看它是什么(是不是房间消息处理器)。
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


print('=== 表地址 0x082E1458 的内存可读性 ===')
r = read_at(0x082E1458, 64)
print('  readable:', 'yes' if r else 'no', (r[:32].hex() if r else ''))

print()
print('=== PE 节表(判断 0x82E1458 属于哪一节) ===')
try:
    import pefile
    pe = pefile.PE(EXE, fast_load=True)
    imgbase = pe.OPTIONAL_HEADER.ImageBase
    rva = 0x082E1458 - imgbase
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            name = s.Name.rstrip(b'\x00').decode('latin1')
            print('  节 %-8s VA=0x%08X VSize=0x%X RawSize=0x%X'
                  % (name, imgbase + s.VirtualAddress,
                     s.Misc_VirtualSize, s.SizeOfRawData))
            off_in = rva - s.VirtualAddress
            print('  表在节内偏移 0x%X, 节 RawSize=0x%X -> %s'
                  % (off_in, s.SizeOfRawData,
                     '在文件初值区内(静态表)' if off_in < s.SizeOfRawData
                     else '超出文件初值(运行期填充/.bss)'))
            foff = s.PointerToRawData + off_in
            if off_in < s.SizeOfRawData:
                with open(EXE, 'rb') as f:
                    f.seek(foff)
                    data = f.read(32)
                print('  文件初值(前32B):', data.hex())
            break
except ImportError:
    print('  (pefile 不可用, 跳过节分析)')

print()
print('=== 0x0810D978 反汇编(0x31 的表项) ===')
code = read_at(0x0810D978, 0x80)
md = Cs(CS_ARCH_X86, CS_MODE_32)
if code:
    for n, ins in enumerate(md.disasm(code, 0x0810D978)):
        print('  %08X  %-20s %s %s' % (ins.address, ins.bytes.hex(),
                                       ins.mnemonic, ins.op_str))
        if n > 25:
            break
else:
    print('  (不可读)')
