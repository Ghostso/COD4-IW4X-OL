"""找 0x7F1060 (房间推送接收入口) 的地址被写到哪里 —— 它经函数指针调用。

搜 dword 0x007F1060 在内存/EXE 里的出现位置。命中处若是表项, 反查表的用途;
若是 `push imm32` / `mov ...,imm32`, 直接给出注册它的代码。

用法: python -I tools/find_recv_entry_refs.py
"""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'

TARGETS = [0x007F1060, 0x007F10C0, 0x007F10E0, 0x007E7C90, 0x006371F0]

regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


def scan_mem(needle):
    hits = []
    for base, size, fn, prot in regions:
        data = blob(fn)
        if len(data) != size:
            continue
        i = data.find(needle)
        while i >= 0:
            if i % 4 == 0:
                hits.append((base + i, prot))
            i = data.find(needle, i + 1)
    return hits


md = Cs(CS_ARCH_X86, CS_MODE_32)

for tgt in TARGETS:
    print('=== 引用 0x%08X ===' % tgt)
    hits = scan_mem(struct.pack('<I', tgt))
    print('  内存 dword 命中: %d' % len(hits))
    for va, prot in hits[:8]:
        # 判断是否落在代码段（prot 含执行位 0x10/0x20/0x40）
        exec_like = bool(prot & 0x10)
        tag = '代码段内(可能是指令立即数)' if exec_like else '数据段(表项)'
        print('    0x%08X  prot=0x%X  %s' % (va, prot, tag))
        code = read_at(va - 0x20, 0x50)
        if code and exec_like:
            for n, ins in enumerate(md.disasm(code, va - 0x20)):
                mark = '  <<<' if ins.address <= va < ins.address + ins.size else ''
                print('       %08X  %-20s %s %s%s'
                      % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
                if n > 12:
                    break
        elif not exec_like:
            dump = read_at(va - 0x10, 0x30)
            if dump:
                print('       附近数据: %s' % dump.hex())
    print()
