"""Disassemble a VA range of the unpacked PE.  usage: python -I dis.py 0xVA [len]
   optional: --fn to follow linear disassembly only."""
import sys, struct
sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe_map import load, va2off

P = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
d, ib, secs = load(P)

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False
md.skipdata = True


def dis(va, n, label=''):
    off = va2off(secs, ib, va)
    code = d[off:off + n]
    if label:
        print('--- %s @%08X ---' % (label, va))
    for ins in md.disasm(code, va):
        print('%08X  %-24s %s %s' % (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))


if __name__ == '__main__':
    va = int(sys.argv[1], 16)
    n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 128
    dis(va, n)
