"""cfg 文件格式鉴定。

**只做测量，不下结论。** 输出的是原始观测：大小、头字节、熵、字节分布、
重复块、可打印串。候选格式一栏由人填，脚本只在有客观指纹时才给提示。

用法：
    python scripts/cfgid.py                          # 扫默认的那批 cfg
    python scripts/cfgid.py TCLS/config/updateconfig.cfg
    python scripts/cfgid.py --all                    # 全盘 *.cfg
    python scripts/cfgid.py --head 256               # 打印更多头字节
"""
import argparse
import collections
import math
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT = [
    'TCLS/config/updateconfig.cfg',
    'TCLS/config/commonconfig.cfg',
    'TCLS/config/dirsystemconfig.cfg',
    'TCLS/TenProtect/config/updateconfig.cfg',
    'TCLS/TenProtect/config/commonconfig.cfg',
    'TCLS/TenProtect/config/version.cfg',
    'Cross/Config/Config.cfg',
    'Cross/Config/GameConfig.cfg',
    'Cross/Config/commonconfig.cfg',
    'Cross/Config/updateconfig.cfg',
    'Cross/LiveUpdate/config/updateconfig.cfg',
    'Cross/LiveUpdate/config/commonconfig.cfg',
    'Cross/Apps/AppList.cfg',
    'Cross/Apps/AppList_back.cfg',
    'Cross/Apps/CQS/CQSGameConfig.cfg',
    'Cross/FileCache/396553549/2a9e5426/registry.cfg',
    'Cross/FileCache/All Users/2a9e5426/registry.cfg',
    'players/config_mp.cfg',
]


def entropy(b):
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def printable_ratio(b):
    if not b:
        return 0.0
    return sum(1 for x in b if 32 <= x < 127 or x in (9, 10, 13)) / len(b)


def nul_ratio(b):
    return (b.count(0) / len(b)) if b else 0.0


MAGICS = [
    (b'\x78\x01', 'zlib (no/low compression)'),
    (b'\x78\x5e', 'zlib (fast)'),
    (b'\x78\x9c', 'zlib (default)'),
    (b'\x78\xda', 'zlib (best)'),
    (b'\x1f\x8b', 'gzip'),
    (b'BZh', 'bzip2'),
    (b'\x04\x22\x4d\x18', 'LZ4 frame'),
    (b'\x28\xb5\x2f\xfd', 'zstd'),
    (b'\x5d\x00\x00', 'LZMA raw (props 0x5d)'),
    (b'\x89PNG', 'PNG'),
    (b'PK\x03\x04', 'ZIP / OOXML / JAR'),
    (b'\xef\xbb\xbf', 'UTF-8 BOM'),
    (b'\xff\xfe', 'UTF-16 LE BOM'),
    (b'\xfe\xff', 'UTF-16 BE BOM'),
    (b'<?xml', 'XML'),
    (b'\xd0\xcf\x11\xe0', 'OLE compound file'),
    (b'SQLite format 3', 'SQLite'),
    (b'\x00\x00\x00\x00', 'zero-filled start'),
]


def magic_of(b):
    hits = []
    for m, name in MAGICS:
        if b.startswith(m):
            hits.append(name)
    # 头部小端 u32 窗口，找"长度字段 == 文件大小"之类的自描述
    return hits


def hexdump(b, n, base=0):
    out = []
    for off in range(0, min(len(b), n), 16):
        chunk = b[off:off + 16]
        hx = ' '.join('%02x' % x for x in chunk)
        asc = ''.join(chr(x) if 32 <= x < 127 else '.' for x in chunk)
        out.append('%04x  %-47s  %s' % (base + off, hx, asc))
    return out


def u32_candidates(b, size):
    """在头部 64 字节里找小端 u32，标出哪些等于文件大小或文件大小-头长。"""
    hits = []
    for off in range(0, min(len(b) - 3, 64), 1):
        v = struct.unpack_from('<I', b, off)[0]
        if v == size:
            hits.append((off, v, '== filesize'))
        elif 0 < v < size and size - v < 4096:
            hits.append((off, v, 'filesize - %d' % (size - v)))
    return hits


def repeated_blocks(b, blk=16):
    """找重复的 16 字节块 —— 全零/全 FF 填充、固定 IV、固定头都会暴露。"""
    c = collections.Counter(b[i:i + blk] for i in range(0, len(b) - blk + 1, blk))
    return [(v, k) for k, v in c.most_common(5) if v > 1]


STR_RE = re.compile(rb'[\x20-\x7e]{6,}')


def strings(b, minlen=6, limit=40):
    return [m.group().decode('ascii', 'replace')
            for m in STR_RE.finditer(b)][:limit]


def report(path, head_bytes):
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if not os.path.exists(full):
        print('!! 不存在：%s' % path)
        return
    b = open(full, 'rb').read()
    size = len(b)
    print('=' * 78)
    print('# %s' % path)
    print('=' * 78)
    print('大小      : %d (0x%X)' % (size, size))
    print('熵        : %.4f / 8.0   (整文件)' % entropy(b))
    for name, n in (('前1K', 1024), ('前4K', 4096)):
        if size >= n:
            print('  熵(%s): %.4f' % (name, entropy(b[:n])))
    print('可打印率  : %.1f%%' % (printable_ratio(b) * 100))
    print('NUL 占比  : %.1f%%' % (nul_ratio(b) * 100))
    mg = magic_of(b)
    print('魔数命中  : %s' % (', '.join(mg) if mg else '无'))
    u = u32_candidates(b, size)
    print('长度字段候选: %s' % ('; '.join('@0x%02x=%d %s' % h for h in u) if u else '无'))
    rb = repeated_blocks(b)
    print('重复16B块 : %s' % ('; '.join('x%d %s' % (v, k.hex()) for v, k in rb) if rb else '无'))
    print('--- 头 %d 字节 ---' % head_bytes)
    for line in hexdump(b, head_bytes):
        print(line)
    if size > head_bytes:
        print('--- 尾 64 字节 ---')
        for line in hexdump(b[-64:], 64, base=size - 64):
            print(line)
    s = strings(b)
    if s:
        print('--- 可打印串 (前%d) ---' % len(s))
        for x in s:
            print('  %s' % x)
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--all', action='store_true', help='全盘扫 *.cfg')
    ap.add_argument('--head', type=int, default=128)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if a.all:
        paths = []
        for dp, dn, fn in os.walk(ROOT):
            for f in fn:
                if f.lower().endswith('.cfg'):
                    paths.append(os.path.relpath(os.path.join(dp, f), ROOT))
        paths.sort()
    elif a.paths:
        paths = a.paths
    else:
        paths = DEFAULT
    for p in paths:
        report(p, a.head)


if __name__ == '__main__':
    main()
