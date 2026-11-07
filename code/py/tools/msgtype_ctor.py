#!/usr/bin/env python3
"""定位每个 dwRoomMessage* 类的构造函数并提取类型号。

方法：
  1. 从 dwroom_serializers.py 拿 (类名, vtable 地址)
  2. 全镜像扫 "mov dword ptr [reg], imm32" 且 imm32 == vtable 地址
     => 那就是构造函数里的 vtable 装填点
  3. 从该点向后扫 0x80 字节，找 "mov [reg+4], imm" 或
     "mov tmp, imm; mov [reg+4], tmp" => 类型号
"""
import re
import struct
import subprocess
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rows():
    out = subprocess.run(
        [sys.executable, "-I", "tools/dwroom_serializers.py"],
        capture_output=True, text=True, encoding="latin1").stdout
    r = []
    for line in out.splitlines():
        m = re.match(r"^(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
                     r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)", line)
        if m:
            r.append((m.group(1), int(m.group(2), 16)))
    return r


def main():
    b = open(DUMP, "rb").read()
    cls = rows()
    # 1) 先给每个 vtable 找装填点
    vt_hits = {}
    for name, vt in cls:
        pat = struct.pack("<I", vt)
        k = 0
        locs = []
        while True:
            i = b.find(pat, k)
            if i < 0:
                break
            # 看是不是 c7 41/40/42.. imm32 形式（前面 2 字节是 c7 xx）
            if i >= 2 and b[i - 2] == 0xC7 and b[i - 1] in (
                    0x01, 0x41, 0x40, 0x42, 0x43, 0x45, 0x46, 0x47,
                    0x02, 0x04, 0x06, 0x07, 0x05):
                locs.append(BASE + i - 2)
            k = i + 1
        if locs:
            vt_hits[name] = locs
        print("%-46s vtable=%#010x  ctor装填点 %d 处 %s" % (
            name, vt, len(locs), [hex(x) for x in locs[:3]]))


if __name__ == "__main__":
    main()
