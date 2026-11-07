"""x86(32位) 调用点 → caller 追踪。

本目标是 PE32 / i386（machine=0x014c），没有 x64 的 .pdata，
函数边界只能靠启发式：
  * 直接调用目标（E8 rel32 的落点）几乎总是函数入口
  * 典型 prologue: 55 8B EC / 6A xx 68 / 83 EC xx / 81 EC / 8B FF 55 8B EC / 56 8B F1 ...
用「调用点之前最近的函数入口」归属函数，再反查谁调用了该函数。

参数恢复：x86 是 cdecl/stdcall，参数在调用前 push。
从调用点往回最多 N 字节反汇编，收集 push/mov 立即数与 RIP 无关的绝对地址。
"""
import struct
import collections

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap

try:
    import capstone
    _md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    _md.detail = False
except Exception:
    _md = None


def text_sec(img):
    return [s for s in img.sections if s['name'] == '.text'][0]


# ---------- 调用图基础 ----------

def direct_call_targets(img):
    """{target_va: [call_site_va, ...]}，只收 E8 rel32。"""
    sec = text_sec(img)
    start, end = sec['raw'], sec['raw'] + sec['rawsize']
    out = collections.defaultdict(list)
    i = img.data.find(b'\xe8', start, end)
    while i >= 0:
        rel = struct.unpack_from('<i', img.data, i + 1)[0]
        src = img.voff(i)
        if src is not None:
            out[src + 5 + rel].append(src)
        i = img.data.find(b'\xe8', i + 1, end)
    return out


def func_starts(img, calls):
    """启发式函数入口集合：直接调用落点 + prologue 特征。"""
    starts = set(calls.keys())
    sec = text_sec(img)
    start, end = sec['raw'], sec['raw'] + sec['rawsize']
    pats = (
        b'\x55\x8b\xec',              # push ebp; mov ebp,esp
        b'\x8b\xff\x55\x8b\xec',      # mov edi,edi; push ebp; mov ebp,esp
        b'\x6a\xff\x68',              # push -1; push imm(SEH)
    )
    for p in pats:
        i = img.data.find(p, start, end)
        while i >= 0:
            v = img.voff(i)
            if v is not None:
                starts.add(v)
            i = img.data.find(p, i + 1, end)
    # 跳到对齐边界的 push xx; mov edi,edi 也算
    return sorted(starts)


def owner_of(starts, va):
    import bisect
    i = bisect.bisect_right(starts, va) - 1
    return starts[i] if i >= 0 else None


# ---------- 反汇编 ----------

def dis(img, va, nbytes):
    if _md is None:
        return []
    o = img.foff(va)
    if o is None:
        return []
    code = img.data[o:o + nbytes]
    return list(_md.disasm(code, va))


def render(ins):
    s = '%08x  %-24s %s %s' % (ins.address,
                               ins.bytes.hex(),
                               ins.mnemonic, ins.op_str)
    return s


def peek_string(img, va, limit=80):
    s = img.cstr(va, limit)
    return s


def backtrace_args(img, call_va, window=140):
    """从 call_va 往回反汇编 window 字节，再往后带上 call 本身。"""
    dis_list = dis(img, call_va - window, window + 16)
    lines = []
    pushes = []
    abs_addrs = []
    for ins in dis_list:
        lines.append(render(ins))
        if ins.mnemonic == 'push':
            pushes.append(ins.op_str)
        # 捕获任何 4 字节绝对地址操作数（ida2 槽 / 全局变量）
        for tok in ins.op_str.replace('[', ' ').replace(']', ' ').replace(',', ' ').split():
            t = tok.strip()
            if t.startswith('0x') and len(t) >= 8:
                try:
                    v = int(t, 16)
                except ValueError:
                    continue
                if 0x10000000 <= v < 0x14000000:
                    abs_addrs.append((ins.address, ins.mnemonic, ins.op_str, v))
    return lines, {'pushes': pushes, 'abs': abs_addrs}


# ---------- 顶层面板 ----------

TARGETS = [
    'GetCommandLineA', 'GetCommandLineW', 'CommandLineToArgvW',
    'GetEnvironmentVariableA', 'GetEnvironmentVariableW', 'ExpandEnvironmentStringsA',
    'GetCurrentDirectoryA', 'GetCurrentDirectoryW',
    'GetFullPathNameA', 'GetFullPathNameW',
    'GetModuleFileNameA', 'GetModuleFileNameW',
    'OpenFileMappingA', 'OpenFileMappingW',
    'MapViewOfFile', 'CreateFileMappingA', 'CreateFileMappingW',
    'CreateMutexA', 'CreateMutexW', 'OpenMutexA', 'OpenMutexW',
    'CreateEventA', 'CreateEventW', 'OpenEventA', 'OpenEventW',
    'FindWindowA', 'FindWindowW', 'PostMessageW', 'SendMessageTimeoutA',
    'SetCurrentDirectoryA', 'SetCurrentDirectoryW',
]


def report(img=None, names=None, show_dis=True):
    if img is None:
        img = Image()
    slots = importmap.build(img)
    xr = importmap.xrefs(img, slots)
    names = names or TARGETS

    # 反向索引：api 短名 -> [slot_rva]
    by_api = collections.defaultdict(list)
    for rva, lab in slots.items():
        api = lab.split('!', 1)[1]
        by_api[api].append(rva)

    calls = None
    for api in names:
        slot_rvas = by_api.get(api) or []
        if not slot_rvas:
            print('%-26s  [未出现在导入槽中]' % api)
            continue
        total = []
        for sr in slot_rvas:
            total += xr.get(sr, [])
        if not total:
            print('%-26s  slot %s  0 个调用点（导入但未静态引用）'
                  % (api, ', '.join('0x%06x' % s for s in slot_rvas)))
            continue
        print('%-26s  slot %s  %d 个调用点:'
              % (api, ', '.join('0x%06x' % s for s in slot_rvas), len(total)))
        for c in sorted(set(total)):
            print('      call @ 0x%06x' % c)
            if show_dis:
                lines, clues = backtrace_args(img, c, 120)
                for l in lines:
                    mark = '  <== CALL' if l.startswith('%08x' % c) else ''
                    print('          ' + l + mark)
                # 把 push 里的绝对地址翻成字符串看看
                seen = set()
                for adr, mn, ops, v in clues['abs']:
                    if v in seen:
                        continue
                    seen.add(v)
                    s = peek_string(img, v)
                    if s:
                        print('          >> 0x%08x = "%s"' % (v, s))
                print()
    return slots, xr


if __name__ == '__main__':
    import sys as _s
    nm = _s.argv[1:] or None
    report(names=nm)
