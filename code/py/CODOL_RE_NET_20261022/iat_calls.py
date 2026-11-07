import struct
from capstone import *
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# walk .text linearly, record FF15 to slots in 0xCA8000..0xCB3000 with resolved target
md = Cs(CS_ARCH_X86, CS_MODE_32)
import collections
res = collections.defaultdict(list)
text_lo, text_hi = 0x1000, 0x8A689A
for ins in md.disasm(d[text_lo:text_hi], B+text_lo):
    if ins.mnemonic in ('call','jmp') and ins.op_str.startswith('dword ptr [0xca'):
        try: slot = int(ins.op_str.split('[')[1].split(']')[0], 16)
        except: continue
        tgt = struct.unpack('<I', d[slot-B:slot-B+4])[0]
        res[(slot,tgt)].append(ins.address)
print('distinct (slot,target) pairs:', len(res))
for (slot,tgt), sites in sorted(res.items(), key=lambda kv: -len(kv[1]))[:60]:
    print('  slot %#010x -> %#010x  n=%d  first=%s' % (slot, tgt, len(sites), [hex(x) for x in sites[:4]]))
