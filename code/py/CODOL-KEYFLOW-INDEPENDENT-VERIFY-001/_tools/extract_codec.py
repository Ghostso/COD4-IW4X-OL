# -*- coding: utf-8 -*-
"""从冻结镜像机器码独立提取 Codec 参数（不读取任何报告的数值）。"""
import struct, hashlib

BIN = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
IMGBASE = 0x400000

class Text(object):
    def __init__(self, path):
        self.d = open(path, 'rb').read()
        self.sha = hashlib.sha256(self.d).hexdigest()
    def off(self, va):
        rva = va - IMGBASE
        assert 0x1000 <= rva < 0x7ac90b, hex(va)
        return rva - 0x1000 + 0x400
    def u32(self, va): return struct.unpack_from('<I', self.d, self.off(va))[0]
    def u8(self, va):  return self.d[self.off(va)]

def scan(tx, start, end):
    """遍历函数序言区，收集常量表与置换表槽位。"""
    consts = {}
    slots = {}
    regs = {}
    va = start
    while va < end:
        op = tx.u8(va)
        if op == 0xC7 and tx.u8(va+1) == 0x45:                       # mov dword [ebp+d8], imm32
            disp = struct.unpack_from('<b', tx.d, tx.off(va+2))[0]
            slots[disp] = tx.u32(va+3)
            va += 7
        elif op == 0x89 and tx.u8(va+1) in (0x45,0x4D,0x55,0x5D,0x7D):  # mov [ebp+d8], r32
            disp = struct.unpack_from('<b', tx.d, tx.off(va+2))[0]
            reg = {0x45:'eax',0x4D:'ecx',0x55:'edx',0x5D:'ebx',0x7D:'edi'}[tx.u8(va+1)]
            slots[disp] = regs.get(reg, 0)
            va += 3
        elif op in (0xB8,0xB9,0xBA,0xBB,0xBF):                        # mov r32, imm32
            rn = {0xB8:'eax',0xB9:'ecx',0xBA:'edx',0xBB:'ebx',0xBF:'edi'}[op]
            regs[rn] = tx.u32(va+1); va += 5
        elif op == 0x8D and tx.u8(va+1) == 0x5A:                      # lea ebx,[edx+d8]
            regs['ebx'] = (regs.get('edx',0) + struct.unpack_from('<b', tx.d, tx.off(va+2))[0]) & 0xffffffff
            va += 3
        else:
            va += 1
    return slots

def extract(tx, fn_start, fn_scan_end, const_start, const_va_end, table_start, table_end, first_slot):
    sl = scan(tx, fn_start, table_end + 8)
    # consts: 5 consecutive imm32 slots occupying [const_start, const_va_end)
    consts = b''
    va = const_start
    while va <= const_va_end:
        disp = struct.unpack_from('<b', tx.d, tx.off(va+2))[0]
        consts += struct.pack('<I', sl[disp]); va += 7
    perm = [sl[first_slot + 4*k] for k in range(20)]
    return consts, perm

if __name__ == '__main__':
    tx = Text(BIN)
    print('binary sha256', tx.sha)
    A_CONST, A_PERM = extract(tx, 0xAA8D70, 0xAA8E36, 0xAA8D9C, 0xAA8DB8, 0xAA8DBF, 0xAA8E35, -0x68)
    B_CONST, B_PERM = extract(tx, 0xAA8BF0, 0xAA8CB7, 0xAA8C19, 0xAA8C35, 0xAA8C3C, 0xAA8CB6, -0x68)
    print('A_CONST', A_CONST.hex())
    print('A_PERM ', A_PERM)
    print('B_CONST', B_CONST.hex())
    print('B_PERM ', B_PERM)
    print('A idx ok', all(0 <= x < 20 for x in A_PERM), 'n', len(A_PERM))
    print('B idx ok', all(0 <= x < 20 for x in B_PERM), 'n', len(B_PERM))
