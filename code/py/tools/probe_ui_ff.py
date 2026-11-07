"""在 ui_mp.ff 里找 Flash(gfx) 资源。

SWF 有三种头:
    FWS  未压缩
    CWS  zlib 压缩
    ZWS  LZMA 压缩

Scaleform 的 gfx 通常仍是 SWF 容器，但头部可能是变体。

本脚本:
  1. 全文件搜 FWS/CWS/ZWS 签名
  2. 搜 scaleform_ash 等资源名
  3. 输出偏移与上下文
"""
import re
import struct
import sys

P = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\main\ui_mp.ff'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

data = open(P, 'rb').read()
print('文件 %d 字节 (%.1f MB)' % (len(data), len(data) / 1048576))

for sig in (b'FWS', b'CWS', b'ZWS', b'GFX', b'CFX'):
    hits = []
    i = data.find(sig)
    while i >= 0 and len(hits) < 20:
        # SWF 头: sig(3) version(1) filelen(u32)
        if i + 8 <= len(data):
            ver = data[i + 3]
            flen = struct.unpack_from('<I', data, i + 4)[0]
            hits.append((i, ver, flen))
        i = data.find(sig, i + 1)
    if hits:
        print()
        print('=== 签名 %s: %d 处 ===' % (sig.decode(), len(hits)))
        for off, ver, flen in hits[:12]:
            sane = 8 <= flen and off + flen <= len(data)
            print('  +0x%08X  version=%d  filelen=%d  合理=%s' % (off, ver, flen, sane))

# 资源名
for nm in (b'scaleform_ash', b'Room', b'ready', b'Ready'):
    cnt = data.count(nm)
    print('  "%s" 出现 %d 次' % (nm.decode(), cnt))

open(OUT + r'\ff_probe.txt' if OUT != '.' else 'ff_probe.txt', 'w',
     encoding='utf-8').write('done\n')
