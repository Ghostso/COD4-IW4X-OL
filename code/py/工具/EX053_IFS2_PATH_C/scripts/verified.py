"""指令边界感知的调用点扫描。

背景：importmap.xrefs() 用字节模式 b'\xff\x15<abs32>' 匹配，
会把嵌在别的指令操作数里的同字节序列误判成调用点
(例：e9 ff 15 bc 22 b0 10  = jmp 0x22d1c9a7，里面的 ff15bc22b010 不是指令)。

本模块改为：从启发式函数入口线性反汇编，只收真正位于指令边界上的
call dword ptr [imm32] / jmp dword ptr [imm32]。
"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone
from pe import Image, IMAGE_BASE
import x86callers as X

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = False


def _starts(img):
    st = set(X.direct_call_targets(img).keys())
    sec = X.text_sec(img)
    a, b = sec['raw'], sec['raw'] + sec['rawsize']
    for p in (b'\x55\x8b\xec', b'\x8b\xff\x55\x8b\xec', b'\x6a\xff\x68'):
        i = img.data.find(p, a, b)
        while i >= 0:
            v = img.voff(i)
            if v is not None:
                st.add(v)
            i = img.data.find(p, i + 1, b)
    return sorted(st)


def scan(img, maxlen=0x3000):
    """返回 {slot_rva: sorted([call_site_va,...])}。

    区间 = [本函数入口, 下一个函数入口)，用线性反汇编扫完整个区间。
    不要在中途遇到 jmp/ret 就 break —— 真实函数里 jmp 之后常有
    仍然可达的代码(条件跳转的落点)，提前 break 会漏掉后半段
    (例：0x719b6a 处的 jmp 之后就藏着 GetCommandLineA 的调用点)。
    """
    starts = _starts(img)
    sec = X.text_sec(img)
    end_fo = sec['raw'] + sec['rawsize']
    out = collections.defaultdict(set)
    for idx, s in enumerate(starts):
        fo = img.foff(s)
        if fo is None:
            continue
        nxt = starts[idx + 1] if idx + 1 < len(starts) else None
        span = (nxt - s) if nxt is not None else maxlen
        if span <= 0:
            span = maxlen
        n = min(span, maxlen, end_fo - fo)
        if n <= 0:
            continue
        for ins in md.disasm(img.data[fo:fo + n], s):
            if ins.mnemonic in ('call', 'jmp') and ins.op_str.startswith('dword ptr [0x'):
                try:
                    tgt = int(ins.op_str[13:-1], 16)
                except ValueError:
                    continue
                if 0x10b02000 <= tgt < 0x10b03000:
                    out[tgt - IMAGE_BASE].add(ins.address)
    return {k: sorted(v) for k, v in out.items()}


if __name__ == '__main__':
    import importmap
    img = Image()
    slots = importmap.build(img)
    v = scan(img)
    want = sys.argv[1:] or None
    for k in sorted(v):
        lab = slots.get(k, '<非导入槽>')
        if want and not any(w in lab for w in want):
            continue
        print('%-22s slot 0x%06x  %3d 处: %s' % (
            lab, k, len(v[k]), ' '.join('0x%06x' % c for c in v[k][:8])))
