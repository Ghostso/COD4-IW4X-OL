"""从实机日志里取一条 219B, 按客户端解析器的布局精确切分。
   usage: python -I _kx_split.py <logfile>
"""
import re
import sys

path = sys.argv[1]
line = None
with open(path, 'r', errors='ignore') as f:
    for ln in f:
        if 'RX 219B FULL' in ln:
            line = ln.strip()
            break
if not line:
    print('未找到 RX 219B FULL')
    sys.exit(1)

m = re.search(r'RX 219B FULL ([0-9A-Fa-f]+)', line)
kx = bytes.fromhex(m.group(1))
print('抓到的 219B 长度 = %d' % len(kx))

print('\n[0..6] 记录头: %s' % kx[0:6].hex())
print('   type = 0x%02X   b1 = 0x%02X   w2 = 0x%04X   w4 = 0x%04X'
      % (kx[0], kx[1], int.from_bytes(kx[2:4], 'little'), int.from_bytes(kx[4:6], 'little')))

off = 6
print('\n[%3d..%3d] cookie(38)      : %s' % (off, off + 38, kx[off:off + 38].hex()))
off += 38
print('[%3d..%3d] bdCommonAddr(67): %s' % (off, off + 67, kx[off:off + 67].hex()))
off += 67
sid = kx[off:off + 8]
print('[%3d..%3d] ★u64 id(8)      : %s   LE=0x%016X' % (off, off + 8, sid.hex(), int.from_bytes(sid, 'little')))
off += 8
key = kx[off:off + 100]
print('[%3d..%3d] ★key blob(100)  : %s' % (off, off + 100, key[:24].hex() + '...'))
off += 100
print('[%3d..%3d] 剩余            : %s' % (off, len(kx), kx[off:].hex() or '(无)'))
print('\n  6+38+67+8+100 = %d' % (6 + 38 + 67 + 8 + 100))
if key[0] == 0x30:
    ln = key[1]
    print('  key blob 内 DER SEQUENCE len=0x%02X → 真公钥 %d 字节, 其余 %d 字节为 0 填充'
          % (ln, 2 + ln, 100 - 2 - ln))
print('\n⇒ 服务端 114B 应当对称: hdr(6) + key(100) + id(8)')
print('   我们当前 out[106]=1 ⇒ id = 0x0000000000000001  <-- 与客户端本端 id 无关')
print('   客户端本端 id = %s (0x%016X)' % (sid.hex(), int.from_bytes(sid, 'little')))
