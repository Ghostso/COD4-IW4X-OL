"""通用追踪工具（x86）。

用法：
    python scripts/chase.py refs  <hexva>          # 谁引用了这个绝对地址（全局变量/槽）
    python scripts/chase.py callers <hexva>        # 谁直接 call 了这个函数入口
    python scripts/chase.py func <hexva>           # 打印某个函数的反汇编（默认 0x300 字节）
    python scripts/chase.py dis <hexva> [n]        # 从地址反汇编 n 字节
    python scripts/chase.py str <hexva>            # 打印该地址处的字符串
    python scripts/chase.py slot <hexva>           # 该 IAT 槽对应的 dll!api
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image, IMAGE_BASE
import importmap
import x86callers as X

CH = 0x10000000   # ImageBase 相对/绝对 判定阈值


def norm(v):
    """统一成 ImageBase 相对 RVA。"""
    return v - IMAGE_BASE if v >= IMAGE_BASE else v


def absv(v):
    return v


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd = sys.argv[1]
    arg = sys.argv[2]
    v = int(arg, 16)
    rva = norm(v)
    img = Image()

    if cmd == 'str':
        print(repr(img.cstr(rva, 200)))
        return

    if cmd == 'dis':
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 128
        for ins in X.dis(img, rva, n):
            print(X.render(ins))
        return

    if cmd == 'slot':
        slots = importmap.build(img)
        for k in (rva, rva + 4, rva - 4):
            if k in slots:
                print('0x%06x -> %s' % (k, slots[k]))
        print('0x%06x -> %s' % (rva, slots.get(rva, '<not a slot>')))
        return

    if cmd == 'refs':
        hits = img.xrefs_to_imm32(rva + IMAGE_BASE)
        print('%d 处引用 0x%08x (rva 0x%06x)' % (len(hits), rva + IMAGE_BASE, rva))
        for fo, va, b in hits:
            ins = list(X.dis(img, va - 12, 24))
            print('  @0x%06x  [%s]' % (va, b.hex()))
            for i in ins:
                print('      ' + X.render(i))
        return

    if cmd in ('callers', 'func'):
        calls = X.direct_call_targets(img)
        if cmd == 'callers':
            cs = calls.get(rva, [])
            print('0x%06x 的函数被 %d 处直接调用：' % (rva, len(cs)))
            for c in cs:
                print('  @0x%06x' % c)
                for ins in list(X.dis(img, c - 24, 32)):
                    print('      ' + X.render(ins))
            return
        # func: 找到调用点推断函数体范围，直接反汇编
        sec = X.text_sec(img)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 0x300
        for ins in X.dis(img, rva, n):
            print(X.render(ins))
        return

    print('unknown cmd', cmd)


if __name__ == '__main__':
    main()
