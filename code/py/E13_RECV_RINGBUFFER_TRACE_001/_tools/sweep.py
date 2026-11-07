"""Robust linear sweep with resync (capstone stops at first undecodable byte)."""
import pefile
from capstone import *

def sweep(md, data, base_va):
    """Yield (va, size, mnemonic, op_str, detail) for every instruction, resyncing on failure."""
    n=len(data); i=0
    while i < n:
        got=False
        for ins in md.disasm(data[i:i+15], base_va+i):
            yield ins
            i += ins.size
            got=True
            break
        if not got:
            i += 1   # resync