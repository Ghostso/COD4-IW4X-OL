"""用正确的 TD 偏移（name-8）解析 MyEventHandler 的 RTTI 链。

TD = 0x00E6EFDC，被引用 2 次。追下去找 COL -> vtable -> 函数体。
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


def off_of(va):
    for n, sva, vs, pr, rs in secs:
        if sva <= va < sva + vs:
            o = pr + (va - sva)
            if o < len(data):
                return o
    return None


def sec_of(o):
    for n, sva, vs, pr, rs in secs:
        if pr <= o < pr + rs:
            return n
    return None


TD = 0x00E6EFDC
needle = struct.pack('<I', TD)
hits = []
i = data.find(needle)
while i >= 0:
    hits.append(i)
    i = data.find(needle, i + 1)

md = Cs(CS_ARCH_X86, CS_MODE_32)
print('TD 0x%08X 被引用 %d 处' % (TD, len(hits)))
for h in hits:
    va = va_of(h)
    print()
    print('--- 引用 @ 文件 0x%X  VA 0x%08X  节 %s ---' % (h, va, sec_of(h)))
    col_off = h - 0x0C
    if col_off < 0:
        continue
    raw = data[col_off:col_off + 0x14]
    sig, off_, cd, ptd, pcd = struct.unpack('<IIIII', raw)
    print('  按 COL 解释: sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X'
          % (sig, off_, cd, ptd, pcd))
    if ptd != TD:
        print('  (pTD 不匹配，不是 COL)')
        continue
    col_va = va_of(col_off)
    print('  ★ COL VA = 0x%08X' % col_va)
    # 找 vtable（vtable[-1] == COL）
    cn = struct.pack('<I', col_va)
    j = data.find(cn)
    nfound = 0
    while j >= 0 and nfound < 5:
        if j % 4 == 0:
            vt_off = j + 4
            v0, v1, v2 = struct.unpack_from('<III', data, vt_off)
            if 0x400000 <= v0 < 0x1000000:
                print('     vtable VA 0x%08X  slots: 0x%08X 0x%08X 0x%08X'
                      % (va_of(j), v0, v1, v2))
                # 反汇编 slot0
                so = off_of(v0)
                if so:
                    print('     --- slot[0] 0x%08X ---' % v0)
                    for n, ins in enumerate(md.disasm(data[so:so + 0x80], v0)):
                        print('       %08X  %-16s %s %s'
                              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                        if n > 16:
                            break
                nfound += 1
        j = data.find(cn, j + 1)
    if not nfound:
        print('     未找到 vtable（COL 未被引用）')
