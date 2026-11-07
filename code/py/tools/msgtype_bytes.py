#!/usr/bin/env python3
"""纯字节模式扫描：找 "C7 /0 disp8 imm32" 且 disp8==0、imm32 落在
dwRoom 位流类 vtable 段。这是 MSVC 的 `mov dword ptr [reg], imm32`。

字节形态: C7 <modrm> 00 <imm32>
  modrm: mod=01 (disp8), reg=000 (/0), rm=000..111
         = 0x40|rm  => 0x40,0x41,0x42,0x43,0x45,0x46,0x47
         (0x44 = SIB 跟随，需另处理)

然后从该处向后 0x80 字节粗扫 "C7 <modrm2> 04 <imm32>"，同样 rm 一致。

用法: python -I tools/msgtype_bytes.py
"""
import struct

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000
RMAP = {0: "eax", 1: "ecx", 2: "edx", 3: "ebx", 5: "ebp", 6: "esi", 7: "edi"}


def main():
    b = open(DUMP, "rb").read()

    vf = []   # (fileoff, reg_rm, imm)
    # mov dword [reg], imm32  =>  C7 <modrm: mod=00 reg=000 rm=reg> <imm32>
    for i in range(len(b) - 6):
        if b[i] != 0xC7:
            continue
        m = b[i + 1]
        if (m & 0xF8) != 0x00:    # mod=00, reg=000  =>  0x00..0x07
            continue
        rm = m & 7
        if rm == 5:               # [disp32] 形式，跳过
            continue
        imm = struct.unpack_from("<I", b, i + 2)[0]
        if 0xdc7400 <= imm < 0xdc8000:
            vf.append((i, rm, imm))
    print("vfptr 装填点（纯字节扫描）%d 处" % len(vf))
    for off, rm, v in vf:
        print("  %#010x [%s] = %#x" % (BASE + off, RMAP.get(rm, rm), v))

    typs = []   # (fileoff, rm, imm, size)
    for i in range(len(b) - 7):
        if b[i] != 0xC7:
            continue
        m = b[i + 1]
        if (m & 0xC7) != 0x40:    # mod=01, reg=000
            continue
        rm = m & 7
        if rm == 4:
            continue
        if b[i + 2] != 0x04:      # disp8 == 4
            continue
        imm = struct.unpack_from("<I", b, i + 3)[0]
        if 0 <= imm <= 0xFF:
            typs.append((i, rm, imm, 4))
    print("[reg+4]=imm32 候选 %d 处（imm<=0xFF）" % len(typs))

    # byte 版本 C6 <modrm> 04 imm8
    typs8 = []
    for i in range(len(b) - 3):
        if b[i] != 0xC6:
            continue
        m = b[i + 1]
        if (m & 0xC7) != 0x40:
            continue
        rm = m & 7
        if rm == 4 or b[i + 2] != 0x04:
            continue
        typs8.append((i, rm, b[i + 3], 1))
    print("[reg+4]=imm8 候选 %d 处" % len(typs8))

    alltyps = typs + typs8
    print("\n=== 配对 ===")
    out = []
    for off, rm, v in vf:
        best = None
        for toff, trm, timm, tsz in alltyps:
            if trm != rm:
                continue
            d = abs(toff - off)
            if d <= 0x80 and (best is None or d < best[0]):
                best = (d, toff, timm, tsz)
        out.append((BASE + off, rm, v, best))
        print("%#010x [%s] = %#x   type=%s" % (
            BASE + off, RMAP[rm], v,
            ("%d(%dB)@%#x" % (best[2], best[3], BASE + best[1]))
            if best else "?"))
    print("\n%d 个构造点，其中 %d 个配到类型号" % (
        len(out), sum(1 for x in out if x[3])))
    with open("_byte_papers/msgtype_bytes.txt", "w", encoding="utf-8") as f:
        for va, rm, v, best in out:
            f.write("%#x\t%s\t%#x\t%s\n" % (
                va, RMAP[rm], v,
                best[2] if best else ""))


if __name__ == "__main__":
    main()
