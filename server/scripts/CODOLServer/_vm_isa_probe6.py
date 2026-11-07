#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 6: capstone xrefs to the AES S-box and the engine window.

This is static disassembly only. It answers:
  * who references the runtime AES S-box at RVA 0x00C84C40?
  * who references / writes the engine window 0x994000..0xCA7890?
  * are there VM dispatch-loop shapes in .text or .tvm0?
"""

import os
import struct
import pefile
from capstone import (Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM,
                      CS_OP_IMM, CS_GRP_JUMP, CS_GRP_CALL)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine',
                    'engine_best.bin')
ENGINE_BASE = 0x00994000
SBOX = 0x00C84C40
WIN_LO, WIN_HI = 0x00994000, 0x00CA7890


def main():
    d = open(DLL, 'rb').read()
    e = open(DUMP, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    secs = [(s.Name.rstrip(b'\x00').decode('latin1'),
             s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections]

    def raw_of(rva):
        for nm, rv, raw, sz in secs:
            if rv <= rva < rv + sz:
                return raw + (rva - rv), nm
        return None, None

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # 1) capstone linear disassembly of the whole engine window, collect
    #    xrefs to the S-box and to the engine window itself.
    print('=== linear disasm over runtime engine window ===')
    insns = list(md.disasm(e, ENGINE_BASE))
    print('decoded %d instructions' % len(insns))
    sbox_refs = []
    win_refs = []
    calls = []
    for ins in insns:
        # immediate references
        for op in ins.operands:
            if op.type == CS_OP_IMM:
                t = op.imm & 0xFFFFFFFF
                if SBOX <= t < SBOX + 0x100:
                    sbox_refs.append((ins.address, ins.mnemonic,
                                      ins.op_str))
                if WIN_LO <= t < WIN_HI:
                    win_refs.append((ins.address, ins.mnemonic,
                                     ins.op_str))
            if op.type == CS_OP_MEM:
                base = op.mem.base
                disp = op.mem.disp & 0xFFFFFFFF
                if SBOX <= disp < SBOX + 0x100:
                    sbox_refs.append((ins.address, ins.mnemonic,
                                      ins.op_str))
                # absolute [disp] on x86-32
                if base == 0 and WIN_LO <= disp < WIN_HI:
                    win_refs.append((ins.address, ins.mnemonic,
                                     ins.op_str))
        if ins.mnemonic in ('call', 'jmp') and ins.op_str.startswith('0x'):
            try:
                t = int(ins.op_str, 16)
            except ValueError:
                t = -1
            if WIN_LO <= t < WIN_HI:
                calls.append((ins.address, t, ins.mnemonic))

    print('')
    print('=== S-box references inside runtime window ===')
    for row in sbox_refs[:80]:
        print('  %08X  %s %s' % row)
    print('total', len(sbox_refs))

    print('')
    print('=== engine-window self references (first 80) ===')
    for row in win_refs[:80]:
        print('  %08X  %s %s' % row)
    print('total', len(win_refs))

    print('')
    print('=== call/jmp targets into engine window (first 80) ===')
    for row in calls[:80]:
        print('  %08X -> %08X  %s' % row)
    print('total', len(calls))

    # 2) find direct absolute write instructions in the runtime window
    print('')
    print('=== runtime instructions writing to an absolute engine address ===')
    writes = []
    for ins in insns:
        if ins.mnemonic.startswith('mov') and len(ins.operands) == 2:
            dst, src = ins.operands
            if dst.type == CS_OP_MEM and dst.mem.base == 0:
                a = dst.mem.disp & 0xFFFFFFFF
                if WIN_LO <= a < WIN_HI:
                    writes.append((ins.address, ins.mnemonic, ins.op_str))
    for row in writes[:80]:
        print('  %08X  %s %s' % row)
    print('total', len(writes))

    # 3) text refs to S-box / window via absolute dwords
    print('')
    print('=== absolute dword refs (disk file) to S-box or engine start ===')
    for target in (SBOX, WIN_LO, 0x009A0000, 0x00C00000):
        pat = struct.pack('<I', target)
        for nm, rv, raw, sz in secs:
            sec = d[raw:raw + sz]
            pos = 0
            shown = 0
            while shown < 30:
                i = sec.find(pat, pos)
                if i < 0:
                    break
                print('  %08X -> %08X  (%s)' % (rv + i, target, nm))
                pos = i + 1
                shown += 1

    # 4) VM dispatch shapes in .text: switch bytecode dispatcher patterns
    print('')
    print('=== candidate dispatch patterns in .text ===')
    txt_rva, txt_raw, txt_sz = next((rv, raw, sz)
                                    for nm, rv, raw, sz in secs
                                    if nm == '.text')
    txt = d[txt_raw:txt_raw + txt_sz]
    pats = {
        'movzx reg,[reg+reg] then jmp table': b'\x0f\xb6\x04\x08',
        'jmp dword [reg*4+disp]': b'\xff\x24\x85',
        'jmp dword [reg*4+disp8]': b'\xff\x24\x8d',
        'push imm32; ret (dispatch)': b'\x68',
    }
    for label, pat in pats.items():
        hits = []
        pos = 0
        while len(hits) < 20:
            i = txt.find(pat, pos)
            if i < 0:
                break
            hits.append(txt_rva + i)
            pos = i + 1
        print('  %-40s %s' % (label,
                              ', '.join('%08X' % h for h in hits)))


if __name__ == '__main__':
    main()
