# -*- coding: utf-8 -*-
import img
for ins in img.dis(0x6327b0, count=90):
    print("  %08X %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
    if ins.address >= 0x6328E8:
        break
