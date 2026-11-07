"""解出全部 MatchMaking 查询类的 RTTI → COL → vtable → 方法。

这 6 个查询类对应 21/x 的不同 task。解出它们的 vtable，
就能从 serialize/deserialize 反推每个 task 的线格式。
"""
import re
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

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


def resolve(name_bytes):
    """名字 -> TD -> COL -> vtable。返回 dict 或 None。"""
    o = data.find(name_bytes)
    if o < 0:
        return None
    name_va = va_of(o)
    # 偏移可能 -8 或 -9，两个都试
    for delta in (8, 9):
        td = name_va - delta
        needle = struct.pack('<I', td)
        i = data.find(needle)
        while i >= 0:
            col_off = i - 0x0C
            if col_off >= 0:
                try:
                    sig, off_, cd, ptd, pcd = struct.unpack_from('<IIIII', data, col_off)
                except struct.error:
                    i = data.find(needle, i + 1)
                    continue
                if sig == 0 and ptd == td and cd < 0x10000:
                    col_va = va_of(col_off)
                    cn = struct.pack('<I', col_va)
                    j = data.find(cn)
                    while j >= 0:
                        if j % 4 == 0:
                            vt_off = j + 4
                            slots = struct.unpack_from('<8I', data, vt_off)
                            if 0x400000 <= slots[0] < 0x1000000:
                                return {'name_va': name_va, 'td': td, 'col': col_va,
                                        'vtable': va_of(j), 'slots': list(slots)}
                        j = data.find(cn, j + 1)
            i = data.find(needle, i + 1)
    return None


TARGETS = [
    b'.?AVMatchMaking_FIND_SERVERS_Query@@',
    b'.?AVMatchMaking_FIND_LOBBIES_BY_PLAYLIST_Query@@',
    b'.?AVMatchMaking_FIND_LOBBIES_BY_MAP_Query@@',
    b'.?AVMatchMaking_FIND_LOBBIES_BY_CHANNEL_Query@@',
    b'.?AVMatchMaking_FIND_MP_CUSTOMIZE_LOBBIES_BY_NAME_Query@@',
    b'.?AVMatchMaking_FIND_MP_CUSTOMIZE_LOBBIES_BY_GAME_TYPE_Query@@',
    b'.?AVMatchMakingQuery@@',
    b'.?AVbdSessionParams@@',
    b'.?AVbdMatchMakingInfo@@',
    b'.?AVMatchMakingInfo@@',
]

md = Cs(CS_ARCH_X86, CS_MODE_32)
lines = ['# MatchMaking 查询类 RTTI 解析', '']

for t in TARGETS:
    nm = t.decode('latin1')
    r = resolve(t)
    print()
    print('=== %s ===' % nm)
    lines.append('## `%s`' % nm)
    lines.append('')
    if not r:
        print('  未解出')
        lines.append('（未解出 RTTI 链）')
        lines.append('')
        continue
    print('  名字 VA=0x%08X  TD=0x%08X  COL=0x%08X  vtable=0x%08X'
          % (r['name_va'], r['td'], r['col'], r['vtable']))
    print('  slots: %s' % [hex(x) for x in r['slots'][:6]])
    lines.append('```')
    lines.append('name_va = 0x%08X' % r['name_va'])
    lines.append('TD      = 0x%08X' % r['td'])
    lines.append('COL     = 0x%08X' % r['col'])
    lines.append('vtable  = 0x%08X' % r['vtable'])
    lines.append('slots   = %s' % [hex(x) for x in r['slots'][:6]])
    lines.append('```')
    lines.append('')
    # 反汇编前两个槽
    for idx, sv in enumerate(r['slots'][:3]):
        if not (0x400000 <= sv < 0x1000000):
            continue
        so = off_of(sv)
        if so is None:
            continue
        print('  --- slot[%d] 0x%08X ---' % (idx, sv))
        lines.append('### slot[%d] @ 0x%08X' % (idx, sv))
        lines.append('```asm')
        cnt = 0
        for ins in md.disasm(data[so:so + 0x200], sv):
            print('    %08X  %-16s %s %s'
                  % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            lines.append('%08X  %-16s %s %s'
                         % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            cnt += 1
            if ins.mnemonic == 'ret' or cnt > 40:
                break
        lines.append('```')
        lines.append('')

open(OUT + r'\matchmaking_classes.md', 'w', encoding='utf-8').write('\n'.join(lines))
print()
print('-> matchmaking_classes.md')
