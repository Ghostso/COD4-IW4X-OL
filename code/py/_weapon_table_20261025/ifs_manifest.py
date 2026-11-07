# -*- coding: utf-8 -*-
"""Print the plaintext manifest of a CODOL .ifs container."""
import struct, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = sys.argv[1]
d = open(P, 'rb').read()
print('file', os.path.basename(P), len(d), 'bytes')
print('magic', d[:4], 'hdr_len', struct.unpack_from('<I', d, 4)[0])
print('u16@0x0a', struct.unpack_from('<H', d, 0x0a)[0])
print('u64 table @0x0c:', [struct.unpack_from('<Q', d, 0x0c + 8 * i)[0] for i in range(8)])
tail_len = struct.unpack_from('<Q', d, 0x4c)[0]
print('tail_len', tail_len, hex(tail_len))
hdr = struct.unpack_from('<I', d, 4)[0]
man = d[hdr:]
end = man.find(b'IWff0100')
print('manifest bytes', end, '-> payload starts at', hex(hdr + end), 'payload len',
      len(d) - (hdr + end) - tail_len)
print('--- manifest ---')
print(man[:end].decode('latin-1', 'replace'))
