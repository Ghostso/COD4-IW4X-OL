# -*- coding: utf-8 -*-
"""找 0x477250 这个"订阅失败日志"函数的**调用者**, 那才是判定成功/失败的地方。

方法: 搜 call rel32 到 0x477250 的位置。函数开头在 0x477250 附近,
先往上找到真正的 prologue(push ebp; mov ebp,esp), 再搜调用。
"""
from pathlib import Path

DUMP = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\LIVE_FULLMEM_20261022\mem\mem_000.bin")
BASE = 0x400000


def find_prologue(b, va, back=0x400):
    """从 va 往回找 push ebp; mov ebp,esp (55 8B EC)。"""
    off = va - BASE
    seg = b[max(0, off - back):off + 0x40]
    best = None
    for i in range(len(seg) - 3):
        if seg[i] == 0x55 and seg[i + 1] == 0x8B and seg[i + 2] == 0xEC:
            best = max(0, off - back) + i
    return (best + BASE) if best is not None else None


def find_callers(b, target_va, limit=12):
    """搜 E8 rel32 指向 target_va。"""
    out = []
    t = target_va
    i = 0
    n = len(b)
    while i < n - 5:
        j = b.find(b"\xE8", i)
        if j < 0:
            break
        rel = int.from_bytes(b[j + 1:j + 5], "little", signed=True)
        if (j + 5 + rel + BASE) == t:
            out.append(j + BASE)
            if len(out) >= limit:
                break
        i = j + 1
    return out


def main():
    b = DUMP.read_bytes()
    print("转储 %.1f MB" % (len(b) / 1048576))

    for probe in (0x477250, 0x477240, 0x477230, 0x477220):
        p = find_prologue(b, probe)
        print("  从 0x%X 往回找 prologue -> %s" % (probe, "0x%X" % p if p else "未找到"))
        if p:
            callers = find_callers(b, p)
            print("     调用者: %s" % (" ".join("0x%X" % c for c in callers) or "(无)"))
            if callers:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
