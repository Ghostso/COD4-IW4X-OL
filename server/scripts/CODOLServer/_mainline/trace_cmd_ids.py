"""看数字 ID（3049/2942/...）在代码里被怎么用。

如果它们被 push 到某个注册函数，就能看到注册机制；
如果只是数据表，说明命令确实没注册。
"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

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
            o = pr + (va - sva)
            if o + 1 < len(data):
                return o
    return None


md = Cs(CS_ARCH_X86, CS_MODE_32)
NUMS = [3049, 2942, 2941, 3014, 3015, 3024, 3023, 3021]

for n in NUMS[:5]:
    needle = struct.pack('<I', n)
    hits = []
    i = data.find(needle)
    while i >= 0 and len(hits) < 8:
        hits.append(i)
        i = data.find(needle, i + 1)
    print('=== %d  出现 %d 次 ===' % (n, len(hits)))
    for h in hits[:4]:
        va = va_of(h)
        # 判断是否在代码段（用 80 字节窗口看是否像指令）
        back = data[max(0, h - 24):h + 16]
        print('  off=0x%X va=%s  上下文=%s' % (h, hex(va) if va else '?', back.hex()))
    print()
