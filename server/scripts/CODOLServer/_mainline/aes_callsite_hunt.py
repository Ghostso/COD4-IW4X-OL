#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aes_callsite_hunt.py -- find code that references the runtime AES S-box, in
order to locate the key material passed to it.

For each S-box hit VA we search the image for absolute DWORD references (the
x86-32 addressing pattern), then disassemble a window around each reference so
the key pointer / key schedule pointer can be read out of the caller.

Run elevated. Read-only.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys

import capstone

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD),
                ('Type', wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MBI), ctypes.c_size_t]


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        prot = int(mbi.Protect)
        if (mbi.State == MEM_COMMIT and not (prot & PAGE_GUARD)
                and (prot & 0xFF) != PAGE_NOACCESS):
            yield base, size, prot
        nxt = base + size
        if nxt <= addr:
            return
        addr = nxt


def read_some(h, base, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                 ctypes.byref(got)):
        return b''
    return buf.raw[:got.value]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sbox-va', type=lambda s: int(s, 0), action='append',
                    required=True)
    ap.add_argument('--context', type=int, default=64)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'callsite_hunt.log'), 'w',
                encoding='utf-8')

    def log(m):
        logf.write(m + '\n')
        logf.flush()
        print(m, flush=True)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False,
                        args.pid)
    log('OpenProcess(%d) -> %s err=%d' % (args.pid, h, ctypes.get_last_error()))
    if not h:
        return 1

    needles = [(va, struct.pack('<I', va)) for va in args.sbox_va]
    refs = []
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    code_regions = []
    for base, size, prot in regions(h):
        # Only mapped-image executable regions are worth disassembling.
        if prot & 0x100:  # PAGE_GUARD already filtered; 0x100 = ?; use 0x20/0x40
            pass
        if (prot & 0xFF) in (0x10, 0x20, 0x40, 0x80) or (prot & 0x100):
            code_regions.append((base, size))

    log('executable regions: %d' % len(code_regions))

    for base, size in code_regions:
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = read_some(h, base + off, want)
            if data:
                for va, needle in needles:
                    start = 0
                    while True:
                        i = data.find(needle, start)
                        if i < 0:
                            break
                        at = base + off + i
                        # look back for a plausible instruction start
                        lo = max(0, i - args.context)
                        chunk = data[lo:i + 8]
                        refs.append({'sbox': va, 'ref_va': at,
                                     'region': base,
                                     'bytes': chunk.hex()})
                        start = i + 1
            off += want

    log('references to S-box: %d' % len(refs))
    out = os.path.join(args.out, 'sbox_refs.jsonl')
    with open(out, 'w', encoding='utf-8') as fh:
        for r in refs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Disassemble a window around the first few references.
    with open(os.path.join(args.out, 'sbox_refs_disasm.txt'), 'w',
              encoding='utf-8') as fh:
        for r in refs[:200]:
            va = r['ref_va']
            data = read_some(h, va - 32, 96)
            if not data:
                continue
            fh.write('=== sbox=0x%08X ref=0x%08X\n' % (r['sbox'], va))
            for ins in md.disasm(data, va - 32):
                fh.write('  %08X  %-20s %s %s\n'
                         % (ins.address, ins.bytes.hex(' '),
                            ins.mnemonic, ins.op_str))
            fh.write('\n')
    log('wrote %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
