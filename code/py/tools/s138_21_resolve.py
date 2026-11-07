#!/usr/bin/env python3
"""s138_21_resolve: 对 21/1、21/12、21/5 的每个 i32 元素, 用 crc32(令牌) 反查它的来源。
令牌库: 二进制里的 ASCII 词 + playlist 明文里的词 (games/模式/地图/playlist 关键字)。
只读 corpus 与镜像, 不写任何受保护文件。
"""
import json
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
IMG = r"E:\codol_re\client_image_20261027.bin"
PLAYLIST = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"

# 复用 113 卷已验证的语法: 只有 0x07 i32 / 0x08 u32 / 0x0a u64 / 0x10 str / 0x13 blob / 0x6b 0x6c arr / 0x03 u8 / 0x06 u16 / 0x01 bool


def parse(b, i=0):
    els = []
    n = len(b)
    while i < n:
        t = b[i]
        i += 1
        if t == 0x00:
            els.append((0x00, None))
            if i >= n:
                return els, i
            continue
        if t in (0x01, 0x03):
            if i + 1 > n: return els, i
            els.append((t, b[i])); i += 1
        elif t in (0x06,):
            if i + 2 > n: return els, i
            els.append((t, int.from_bytes(b[i:i+2], 'little'))); i += 2
        elif t in (0x07, 0x08):
            if i + 4 > n: return els, i
            els.append((t, int.from_bytes(b[i:i+4], 'little', signed=(t == 0x07)))); i += 4
        elif t in (0x09, 0x0a):
            if i + 8 > n: return els, i
            els.append((t, int.from_bytes(b[i:i+8], 'little', signed=(t == 0x09)))); i += 8
        elif t == 0x10:
            j = b.find(b"\x00", i)
            if j < 0: return els, i
            els.append((t, b[i:j])); i = j + 1
        elif t == 0x13:
            if i < n and b[i] == 0x08:
                i += 1                      # 子标记 0x08(u32 长度类型)
            if i + 4 > n: return els, i
            L = int.from_bytes(b[i:i+4], 'little'); i += 4
            els.append((t, b[i:i+L])); i += L
        elif t in (0x6b, 0x6c):
            if i < n and b[i] == 0x08:
                i += 1
            if i + 4 > n: return els, i
            L = int.from_bytes(b[i:i+4], 'little'); i += 4
            body = b[i:i+L]; i += L
            tail = int.from_bytes(b[i:i+4], 'little'); i += 4
            els.append((t, (body, tail)))
        else:
            return els, i
    return els, i


def build_wordbank():
    wb = {}
    d = open(IMG, 'rb').read()
    for m in re.finditer(rb'[ -~]{2,60}', d):
        s = m.group()
        wb.setdefault(zlib.crc32(s) & 0xffffffff, set()).add(s.decode('latin1'))
    t = open(PLAYLIST, encoding='latin1').read()
    for m in re.finditer(r'[A-Za-z_][A-Za-z0-9_\.\-]{1,60}', t):
        s = m.group().encode('latin1')
        wb.setdefault(zlib.crc32(s) & 0xffffffff, set()).add(s.decode('latin1'))
    return wb


def main():
    wb = build_wordbank()
    corpus = json.load(open(CORPUS, encoding='utf-8'))
    want = sys.argv[1] if len(sys.argv) > 1 else "21/1"
    svc, task = [int(x) for x in want.split('/')]
    recs = [r for r in corpus if r['svc'] == svc and r['task'] == task]
    print("=== %s  n=%d ===" % (want, len(recs)))
    shown = {}
    for r in recs:
        b = bytes.fromhex(r['payload'])
        els, _ = parse(b)
        sig = tuple((t, (v if not isinstance(v, (bytes, tuple)) else None)) for t, v in els)
        if sig in shown:
            continue
        shown[sig] = r['run']
        print("--- run=%s len=%d els=%d" % (r['run'], len(b), len(els)))
        for i, (t, v) in enumerate(els):
            if t in (0x07, 0x08):
                u = v & 0xffffffff
                w = wb.get(u)
                note = ("  <= crc32(%s)" % ",".join(sorted(w)[:3])) if w else ""
                print("   #%02d 0x%02x=%d 0x%08X%s" % (i, t, v, u, note))
            elif t == 0x0a:
                u = v & 0xffffffffffffffff
                print("   #%02d 0x0a=%d 0x%016X" % (i, v, u))
            elif t == 0x10:
                print("   #%02d 0x10=%r" % (i, v))
            elif t == 0x13:
                print("   #%02d 0x13 len=%d %s" % (i, len(v), v[:24].hex()))
            elif t in (0x6b, 0x6c):
                print("   #%02d 0x%02x bodylen=%d tail=%d" % (i, t, len(v[0]), v[1]))
            else:
                print("   #%02d 0x%02x=%r" % (i, t, v))
        print()


if __name__ == "__main__":
    main()
