"""用 EXE 文件（不是内存镜像）完整解析 AS_* 类的 RTTI 链。

文件偏移 0x762xxx 处有 RTTI 名。PE 里 .rdata 的 VA = 0x400000 + RVA。
先算 RVA，再按 PE 节表映射到文件偏移，最后找 COL 与 vtable。

关键：之前用内存镜像 VA 0xE76Cxx 搜引用失败，
      是因为那次快照里这些名字是**运行时构造的副本**，
      而静态 RTTI 在文件里根本没被加载到那个地址。
"""
import struct
import sys

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
import pefile

pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = []
for s in pe.sections:
    secs.append((s.Name.rstrip(b'\x00').decode('latin1'),
                 base + s.VirtualAddress,
                 s.Misc_VirtualSize,
                 s.PointerToRawData,
                 s.SizeOfRawData))

data = open(EXE, 'rb').read()


def va_of_off(off):
    for name, va, vsz, praw, rsz in secs:
        if praw <= off < praw + rsz:
            return va + (off - praw)
    return None


def off_of_va(va):
    for name, sva, vsz, praw, rsz in secs:
        if sva <= va < sva + vsz:
            o = praw + (va - sva)
            if o < len(data):
                return o
    return None


TARGETS = ['AS_SetReadyState', 'AS_GetReadyState', 'AS_IsRoomHost',
           'AS_StartMatch', 'AS_VoteMap', 'AS_ChangeTeam']

print('%-20s %-12s %-12s' % ('类', '文件偏移', 'VA'))
info = {}
for t in TARGETS:
    nm = ('.?AV' + t + '@@').encode()
    off = data.find(nm)
    if off < 0:
        print('%-20s 未找到' % t)
        continue
    va = va_of_off(off)
    info[t] = (off, va)
    print('%-20s 0x%08X   0x%08X' % (t, off, va))

print()
print('=== 找 Complete Object Locator ===')
# COL 结构: sig(4) offset(4) cdOffset(4) pTD(4) pCD(4)
td_lo = {}

for t, (off, va) in info.items():
    td = va - 9
    td_lo[t] = td
    needle = struct.pack('<I', td)
    hits = []
    i = data.find(needle)
    while i >= 0 and len(hits) < 10:
        # COL 的 pTD 在 +0x0C
        col_off = i - 0x0C
        if col_off >= 0:
            sig, off_, cd = struct.unpack_from('<III', data, col_off)
            if sig == 0 and cd < 0x10000:
                hits.append((col_off, va_of_off(col_off)))
        i = data.find(needle, i + 1)
    print('%-20s TD=0x%08X  COL 候选 %d: %s'
          % (t, td, len(hits),
             [('0x%08X' % h[1]) if h[1] else '?' for h in hits[:3]]))

print()
print('=== 找 vtable（vtable[-1] == COL）===')
for t, (off, va) in info.items():
    td = td_lo[t]
    needle = struct.pack('<I', td)
    i = data.find(needle)
    found = False
    while i >= 0 and not found:
        col_off = i - 0x0C
        if col_off >= 0:
            sig, off_, cd = struct.unpack_from('<III', data, col_off)
            if sig == 0 and cd < 0x10000:
                col_va = va_of_off(col_off)
                if col_va:
                    cn = struct.pack('<I', col_va)
                    j = data.find(cn)
                    while j >= 0:
                        if j % 4 == 0:
                            vt_off = j + 4
                            v0, v1 = struct.unpack_from('<II', data, vt_off)
                            if 0x400000 <= v0 < 0x1000000:
                                print('%-20s COL=0x%08X vtable=0x%08X  slots=[0x%08X, 0x%08X]'
                                      % (t, col_va, va_of_off(j), v0, v1))
                                found = True
                                break
                        j = data.find(cn, j + 1)
        i = data.find(needle, i + 1)
    if not found:
        print('%-20s 未解出 vtable' % t)
