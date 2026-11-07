"""打印任意 PE 的导出表 + 过滤后的字符串。

用法：
    python scripts/pe_info.py <dll>            # 导出表
    python scripts/pe_info.py <dll> --strings  # 导出表 + 字符串
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imports_of import PE

# 只保留有线索价值的字符串
KEEP = re.compile(
    r'(?i)(https?://|udp://|tcp://|\d+\.\d+\.\d+\.\d+|\.qq\.com|\.tencent|'
    r'connect|socket|login|login_|patch|update|gate|server|addr|host|port|'
    r'stun|turn|relay|proxy|disconnect|timeout|retry|handshake|auth|token|'
    r'\.ini$|\.dat$|\.tdr$|\.xml$|session|channel|room|match|game|player)')


def exports(path):
    p = PE(path)
    d = p.data
    dd = p.opt + (0x70 if p.is64 else 0x60)
    exp_rva, exp_size = struct.unpack_from('<II', d, dd)
    if not exp_rva:
        return []
    o = p.off(exp_rva)
    if o is None:
        return []
    # IMAGE_EXPORT_DIRECTORY: +0x0c Name, +0x10 Base, +0x18 #Funcs, +0x1c #Names,
    # +0x20 AddrOfFunctions, +0x24 AddrOfNames, +0x28 AddrOfNameOrdinals
    nfunc, nname = struct.unpack_from('<II', d, o + 0x14)[0], 0
    base, nfunc, nname = struct.unpack_from('<III', d, o + 0x10)
    aof, aon, aoo = struct.unpack_from('<III', d, o + 0x1c)
    fo, no, oo = p.off(aof), p.off(aon), p.off(aoo)
    out = []
    for i in range(min(nname, 4096)):
        if fo is None or no is None or oo is None:
            break
        frva, = struct.unpack_from('<I', d, fo + i * 4)
        nrva, = struct.unpack_from('<I', d, no + i * 4)
        ordi, = struct.unpack_from('<H', d, oo + i * 2)
        nm = p.cstr(nrva) or '?'
        out.append((base + ordi, nm, frva))
    out.sort()
    return out


def strings(path, minlen=5):
    with open(path, 'rb') as f:
        d = f.read()
    # ASCII
    res = set()
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, d):
        s = m.group().decode('latin1')
        if KEEP.search(s):
            res.add(s[:120])
    # UTF-16LE
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % minlen, d):
        try:
            s = m.group().decode('utf-16le')
        except Exception:
            continue
        if KEEP.search(s):
            res.add(s[:120])
    return sorted(res)


def main():
    path = sys.argv[1]
    do_str = '--strings' in sys.argv
    print('=== %s' % path)
    ex = exports(path)
    if ex:
        print('--- 导出 (%d) ---' % len(ex))
        line = []
        for _, nm, _ in ex:
            line.append(nm)
            if len(line) == 6:
                print('    ' + ', '.join(line))
                line = []
        if line:
            print('    ' + ', '.join(line))
    else:
        print('(无导出或导出表不可读)')
    if do_str:
        ss = strings(path)
        print('--- 命中字符串 (%d) ---' % len(ss))
        for s in ss:
            print('    ' + s)


if __name__ == '__main__':
    main()
