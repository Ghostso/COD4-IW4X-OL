import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# all imm writes to state
print('=== writes to 0x84ABA60 (conn SM state) ===')
for i in range(0x7F2000-B, 0x7F4000-B):
    if d[i:i+2]==b'\xc7\x05' and struct.unpack_from('<I',d,i+2)[0]==0x84ABA60:
        imm=struct.unpack_from('<I',d,i+6)[0]
        print('  %#010x -> state %d' % (B+i, imm))
print()
print('=== writes to 0x84ABA50 (DW state) in 0x7F25xx-0x7F40xx ===')
for i in range(0x7F2000-B, 0x7F4000-B):
    if d[i:i+2]==b'\xc7\x05' and struct.unpack_from('<I',d,i+2)[0]==0x84ABA50:
        imm=struct.unpack_from('<I',d,i+6)[0]
        print('  %#010x -> %d' % (B+i, imm))
