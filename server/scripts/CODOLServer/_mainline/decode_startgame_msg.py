"""完整反汇编 dwRoomMessageStartGame 的序列化函数 (vf0 @ 0x00625BE0)。

目标: 解出这条消息写入网络时, 每个字段的位宽与顺序 —— 这样才能构造
      客户端能接受的 StartGame 消息。

已确认的 API:
  0xB77B10  writeBits(v)          —— 写 v 位 (内部 call 0xB77A70)
  0xB777C0  writeData(ptr, nbits) —— 写 nbits 位的数据
  0xB774E0  readBits()            —— 读方向
"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = {}
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions[int(p[0], 16)] = (int(p[1], 16), p[4])

CACHE = {}


def blob(b):
    if b not in CACHE:
        CACHE[b] = open(os.path.join(D, regions[b][1]), 'rb').read()
    return CACHE[b]


def read_at(va, n):
    for base, (size, fn) in regions.items():
        if base <= va < base + size and va + n <= base + size:
            return blob(base)[va - base:va - base + n]
    return None


API = {
    0xB77B10: 'writeBits',
    0xB777C0: 'writeData',
    0xB774E0: 'readBits',
    0xB77A70: 'writeBitsCore',
}


def dump(va, nbytes, label):
    code = read_at(va, nbytes)
    print()
    print('===== %s @ 0x%08X =====' % (label, va))
    if not code:
        print('  (不可读)')
        return
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    recent_push = []
    for ins in md.disasm(code, va):
        line = '  %08X  %-26s %s %s' % (ins.address, ins.bytes.hex(),
                                        ins.mnemonic, ins.op_str)
        if ins.mnemonic == 'push':
            recent_push.append(ins.op_str)
        if ins.mnemonic == 'call':
            try:
                tgt = int(ins.op_str, 16)
            except ValueError:
                tgt = None
            if tgt in API:
                line += '   <<< %s  args=%s' % (API[tgt], recent_push[-3:])
                recent_push = []
            elif tgt is not None:
                recent_push = []
        if ins.mnemonic in ('ret',):
            print(line)
            break
        print(line)
        if ins.address - va > nbytes - 8:
            break


# StartGame vf0 = 序列化 (写)
dump(0x00625BE0, 420, 'dwRoomMessageStartGame :: serialize')
# StartGame vf1 = 反序列化 (读)
dump(0x00625CE0, 260, 'dwRoomMessageStartGame :: deserialize')
