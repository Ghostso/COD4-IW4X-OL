# -*- coding: utf-8 -*-
"""015: enumerate vtables (runs of code pointers in data) and inspect slot +0x24."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa

CODE_LO = BASE + 0x1000
CODE_HI = BASE + 0xA16000


def is_code(va):
    return CODE_LO <= va < CODE_HI


def ret_cleanup(va, limit=0x600):
    """Return stack cleanup bytes if function has a simple ret, else None."""
    code = DATA[va - BASE: va - BASE + limit]
    if len(code) < 16:
        return None
    insns = list(MD.disasm(code, va))
    if not insns:
        return None
    if insns[0].mnemonic not in ("push", "sub", "mov", "and", "xor", "lea",
                                 "jmp", "test", "cmp", "fld", "pop", "add"):
        return None
    for ins in insns:
        if ins.mnemonic == "ret":
            if ins.op_str:
                try:
                    return int(ins.op_str, 16)
                except ValueError:
                    return -1
            return 0
        if ins.mnemonic in ("call",) and ins.operands and ins.operands[0].type == 2:
            continue
    return None


def main():
    n = len(DATA) // 4
    vals = struct.unpack_from("<%dI" % n, DATA, 0)
    runs = []
    cur = None
    for i, v in enumerate(vals):
        if is_code(v) and v % 4 == 0:
            if cur is None:
                cur = [i, i, [v]]
            else:
                cur[1] = i
                cur[2].append(v)
        else:
            if cur is not None and cur[1] - cur[0] >= 2:
                runs.append(cur)
            cur = None
    if cur is not None and cur[1] - cur[0] >= 2:
        runs.append(cur)
    print("vtable-like runs: %d" % len(runs))
    slot_idx = 9  # +0x24
    for st, en, v in runs:
        if len(v) <= slot_idx:
            continue
        base_va = BASE + st * 4
        fn = v[slot_idx]
        rc = ret_cleanup(fn)
        # only report runs whose +0x24 target exists and is a plain function
        if rc is None:
            continue
        first = next(MD.disasm(DATA[fn - BASE: fn - BASE + 16], fn), None)
        print("vtab 0x%08X len=%d  +0x24=0x%08X ret=%s   %s %s"
              % (base_va, len(v), fn, rc, first.mnemonic if first else "?",
                 first.op_str if first else ""))


if __name__ == "__main__":
    main()
