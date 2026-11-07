"""解析 Cross\\Logs\\*.tlg —— 只做提取，不下结论。

.tlg 是二进制记录流，不是文本日志。里面同时有三种东西：
  1. 窄字节 ASCII 串（配置 XML 片段、路径、URL）
  2. 宽字节 UTF-16LE 串（地址字面量、模块名、路径）
  3. 原始内存缓冲（可能含 deflate 表、BMP 像素、XMP 元数据）

本脚本把这三类分别抽出来去重落盘，供人工比对。
用法： python scripts/tlg_parse.py
"""
import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'scripts', '_out')
LOGS = [
    'Cross/Logs/CrossProxy.tlg',
    'Cross/Logs/CrossProxy.tlg.1',
    'Cross/Logs/CrossProxy.tlg.2',
    'Cross/Logs/codomp_client_shipretail.tlg',
]

NARROW_RE = re.compile(rb'[\x20-\x7e]{6,}')
WIDE_RE = re.compile(rb'(?:[\x20-\x7e]\x00){5,}')
ADDR_RE = re.compile(rb'0x[0-9A-F]{5,8}')


def narrow(b):
    return set(m.group().decode('ascii', 'replace') for m in NARROW_RE.finditer(b))


def wide(b):
    return set(m.group().decode('utf-16-le', 'replace') for m in WIDE_RE.finditer(b))


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for rel in LOGS:
        full = os.path.join(ROOT, rel)
        if not os.path.exists(full):
            print('!! 缺 %s' % rel)
            continue
        b = open(full, 'rb').read()
        tag = rel.split('/')[-1].replace('.', '_')
        ns, ws = narrow(b), wide(b)
        addr = collections.Counter(
            m.group().decode('ascii') for m in ADDR_RE.finditer(b))
        io.open(os.path.join(OUT, 'narrow_%s.txt' % tag), 'w',
                encoding='utf-8').write('\n'.join(sorted(ns)))
        io.open(os.path.join(OUT, 'wide_%s.txt' % tag), 'w',
                encoding='utf-8').write('\n'.join(sorted(ws)))
        print('%-34s size=%-9d narrow=%-6d wide=%-6d uniq_addr=%d'
              % (rel, len(b), len(ns), len(ws), len(addr)))
        print('   addr top: %s' % addr.most_common(10))


if __name__ == '__main__':
    main()
