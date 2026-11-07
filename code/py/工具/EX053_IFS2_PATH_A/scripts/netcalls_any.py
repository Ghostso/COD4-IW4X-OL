# -*- coding: utf-8 -*-
"""任意 PE 的「网络 API 调用点 / caller」扫描（**只读**）。

为什么需要它：
  netcallers.py 与 x86callers.py 都 `from pe import Image` 并硬编码
  IMAGE_BASE=0x10000000 / IAT_LO,HI=0xb02000,0xb07000 —— 只服务
  codoMP_client_shipRetailBase.dll（pe.py 第 11 行 PE_OFF=0x110 也是写死的）。
  对 ProtocalHandler.dll / TenBase.dll / p2papp.dll 需要一个**参数化**版本。

判据（与 netcallers.py 同一套，逐条可复核）：
  1) dir1 导入描述符数组 -> 每个 DLL 的 FirstThunk = **IAT 槽数组 RVA**，
     槽 i 的 RVA = FirstThunk + i*4；槽值来自 ILT（OriginalFirstThunk or FirstThunk），
     高位 1<<31 = 序号导入，低 16 位为序号 —— 与 peprobe.py:131-138 同法。
  2) 序号用项目权威表 scripts/importmap.py 的 WS2_32_ORD / WSOCK32_ORD 翻名
     （**必须按 DLL 分开**，两表只在 10/11/12 分歧）。
  3) capstone 线性解码 + 遇非法字节跳 1 再同步，只统计真解出的
     `call dword ptr [imm32]`（FF 15）；imm32 减去本 PE 自己的 ImageBase 后
     落在槽数组内才计入。`jmp dword ptr [imm32]`（FF 25）单独列为「导出桩」。
  4) 归属：调用点之前最近的启发式函数入口（E8 直接调用落点 + 典型 prologue）。
     **这是启发式，不是调试信息** —— 只作 caller 归属，不作语义判据。

用法:
    python scripts/netcalls_any.py <pe路径> [<pe路径> ...]
    python scripts/netcalls_any.py --all <pe路径>        # 连非网络槽也列
输出: 标准输出（不落盘、不修改任何文件）
"""
import os
import re
import sys
import bisect
import struct
import collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importmap  # noqa: E402  —— 只借它的两张权威序号表

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    _md = Cs(CS_ARCH_X86, CS_MODE_32)
    _md.detail = False
except Exception as e:                                   # pragma: no cover
    _md = None
    print('!! capstone 不可用：%r' % (e,))

RE_DW = re.compile(r'^dword ptr \[(.*?)\]$')

# 网络面关键词（与 netcallers.NET17 + NET_EXTRA 同源）
NET_KEY = ('socket', 'connect', 'send', 'recv', 'bind', 'listen', 'accept',
           'select', 'WSA', 'hton', 'ntoh', 'inet_', 'getaddrinfo',
           'getnameinfo', 'freeaddrinfo', 'gethost', 'setsockopt', 'getsockopt',
           'shutdown', 'closesocket', 'ioctlsocket')


class PE(object):
    """标准 PE32 解析（PE 头偏移从 0x3c 读，不写死）。"""

    MAXDESC = 4096
    MAXTHUNK = 200000

    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        d = self.data
        if len(d) < 0x40 or d[:2] != b'MZ':
            raise ValueError('no MZ')
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        if d[pe:pe + 4] != b'PE\0\0':
            raise ValueError('no PE')
        self.pe = pe
        nsec, = struct.unpack_from('<H', d, pe + 6)
        optsz, = struct.unpack_from('<H', d, pe + 0x14)
        self.ts, = struct.unpack_from('<I', d, pe + 8)
        opt = pe + 0x18
        magic, = struct.unpack_from('<H', d, opt)
        self.is64 = (magic == 0x20b)
        if self.is64:
            raise ValueError('本工具只做 PE32')
        self.imagebase, = struct.unpack_from('<I', d, opt + 0x1c)
        self.entry, = struct.unpack_from('<I', d, opt + 0x10)
        self.sizeimage, = struct.unpack_from('<I', d, opt + 0x38)
        self.namedir, = struct.unpack_from('<I', d, opt + 0x5c)
        dd = opt + 0x60
        self.dd = []
        for i in range(min(self.namedir, 16)):
            self.dd.append(struct.unpack_from('<II', d, dd + i * 8))
        sp = pe + 0x18 + optsz
        self.secs = []
        for i in range(nsec):
            o = sp + i * 40
            nm = d[o:o + 8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, roff = struct.unpack_from('<IIII', d, o + 8)
            ch, = struct.unpack_from('<I', d, o + 36)
            self.secs.append({'name': nm, 'va': va, 'vsize': vsz,
                              'raw': roff, 'rawsize': rsz, 'ch': ch})

    def off(self, rva):
        for s in self.secs:
            if s['va'] <= rva < s['va'] + max(s['vsize'], s['rawsize']):
                o = s['raw'] + (rva - s['va'])
                return o if o < s['raw'] + s['rawsize'] else None
        return None

    def rd(self, rva, n):
        o = self.off(rva)
        return None if o is None else self.data[o:o + n]

    def u32(self, rva):
        b = self.rd(rva, 4)
        return struct.unpack_from('<I', b)[0] if b and len(b) == 4 else None

    def cstr(self, rva, n=256):
        b = self.rd(rva, n)
        if b is None:
            return None
        z = b.find(b'\0')
        return b[:z if z >= 0 else len(b)].decode('latin1', 'replace')

    def rva_of_off(self, o):
        for s in self.secs:
            if s['raw'] <= o < s['raw'] + s['rawsize']:
                return s['va'] + (o - s['raw'])
        return None

    def text_sections(self):
        """可执行的节（IMAGE_SCN_MEM_EXECUTE=0x20000000）。"""
        return [s for s in self.secs
                if s['ch'] & 0x20000000 and s['rawsize'] > 0]


def ord_map_for(dll):
    """按 DLL 选权威序号表。返回 None 表示不适用（不猜）。"""
    if dll is None:
        return None
    dl = dll.lower()
    if dl.startswith('ws2_32'):
        return importmap.WS2_32_ORD
    if dl.startswith('wsock32'):
        return importmap.WSOCK32_ORD
    return None


def build_slots(pe, resolve_ord=True):
    """{iat_slot_rva: 'DLL!name'}；name 前加 '?' 表示由序号 + 表推导。"""
    slots = {}
    if not pe.dd[1][0]:
        return slots
    o = pe.off(pe.dd[1][0])
    if o is None:
        return slots
    d = pe.data
    for i in range(PE.MAXDESC):
        p = o + i * 20
        if p + 20 > len(d):
            break
        oft, ts, fc, name_rva, ft = struct.unpack_from('<IIIII', d, p)
        if oft == 0 and name_rva == 0 and ft == 0:
            break
        dll = pe.cstr(name_rva) if name_rva else None
        if ft == 0:
            continue
        om = ord_map_for(dll) if resolve_ord else None
        walk = oft or ft
        for j in range(PE.MAXTHUNK):
            v = pe.u32(walk + j * 4)
            if v is None or v == 0:
                break
            slot_rva = ft + j * 4
            if v & 0x80000000:
                num = v & 0xffff
                if om and num in om:
                    nm = '?%s' % om[num]
                else:
                    nm = 'ORD#%d' % num
            else:
                s = pe.cstr(v + 2, 128)
                nm = s if s else '?'
            slots[slot_rva] = '%s!%s' % (dll, nm)
    return slots


def iat_ranges(pe):
    """dir12 给的 IAT 区间（用于「槽值是否在 IAT 内」的旁证）。"""
    if pe.dd[12][0]:
        return (pe.dd[12][0], pe.dd[12][0] + pe.dd[12][1])
    return (0, 0)


def scan_calls(pe, slots):
    """线性解码所有可执行节，返回 (call 列表, jmp 列表, 统计)。

    call: (va, slot_rva, api, secname)；jmp: 同上（导出/转发桩）。
    """
    calls = []
    jmps = []
    stats = dict(insn=0, bad=0, secs=0)
    base = pe.imagebase
    for s in pe.text_sections():
        stats['secs'] += 1
        buf = pe.data[s['raw']:s['raw'] + s['rawsize']]
        pos = 0
        n = len(buf)
        while pos < n:
            chunk = buf[pos:pos + (1 << 16)]
            i = 0
            last_good = 0
            while i < len(chunk):
                got = 0
                for (addr, size, mn, ops) in _md.disasm_lite(chunk[i:], s['va'] + pos + i):
                    stats['insn'] += 1
                    got = (addr - (s['va'] + pos + i)) + size
                    if mn in ('call', 'jmp'):
                        m = RE_DW.match(ops)
                        if m:
                            t = m.group(1).strip()
                            if t.startswith('0x'):
                                try:
                                    v = int(t, 16)
                                except ValueError:
                                    continue
                                if base <= v < base + pe.sizeimage + 0x1000:
                                    r = v - base
                                    if r in slots:
                                        rec = (addr, r, slots[r], s['name'])
                                        (calls if mn == 'call' else jmps).append(rec)
                if got == 0:
                    i += 1
                    stats['bad'] += 1
                else:
                    i += got
                    last_good = i
            pos += last_good if last_good else len(chunk)
    return calls, jmps, stats


def func_starts(pe):
    """启发式函数入口：E8 落点 + 典型 prologue。**启发式，非调试信息。**"""
    starts = set()
    for s in pe.text_sections():
        buf = pe.data[s['raw']:s['raw'] + s['rawsize']]
        base = s['va']
        i = buf.find(b'\xe8')
        while i >= 0:
            if i + 5 <= len(buf):
                rel = struct.unpack_from('<i', buf, i + 1)[0]
                tgt = base + i + 5 + rel
                top = pe.off(tgt)
                if top is not None:
                    starts.add(tgt)
            i = buf.find(b'\xe8', i + 1)
        for pat in (b'\x55\x8b\xec', b'\x8b\xff\x55\x8b\xec', b'\x6a\xff\x68',
                    b'\x83\xec', b'\x81\xec', b'\x53\x8b\xdc', b'\x56\x8b\xf1'):
            j = buf.find(pat)
            while j >= 0:
                starts.add(base + j)
                j = buf.find(pat, j + 1)
    return sorted(starts)


def owner_of(starts, va):
    i = bisect.bisect_right(starts, va) - 1
    return starts[i] if i >= 0 else None


def pe_digest(pe):
    import hashlib
    h = hashlib.sha256(pe.data).hexdigest()[:16]
    return '%s  %d 字节  ImageBase=0x%08x  SizeOfImage=0x%x  TimeDateStamp=0x%08x  sha256[:16]=%s' % (
        os.path.basename(pe.path), len(pe.data), pe.imagebase, pe.sizeimage, pe.ts, h)


def report(path, show_all=False):
    pe = PE(path)
    print('=' * 78)
    print(pe.path)
    print(pe_digest(pe))
    slots = build_slots(pe)
    print('dir1 导入槽合计 %d 个；dir12 IAT rva=0x%x size=0x%x'
          % (len(slots), pe.dd[12][0], pe.dd[12][1]))
    if pe.dd[13][0]:
        print('dir13（延迟导入）rva=0x%x size=0x%x  —— 本工具**未**扫描延迟导入槽'
              % (pe.dd[13][0], pe.dd[13][1]))
    if not slots:
        print('!! dir1 无可解析导入槽（可能是 peprobe 同款的非标准导入）——停止，不猜。')
        return
    calls, jmps, stats = scan_calls(pe, slots)
    print('扫描：可执行节 %d 个，线性解出指令 %d 条，重同步 %d 次' %
          (stats['secs'], stats['insn'], stats['bad']))
    print('命中：call dword ptr [槽] %d 处；jmp dword ptr [槽] %d 处（转发桩）'
          % (len(calls), len(jmps)))

    by_api = collections.defaultdict(list)
    for rec in calls:
        by_api[rec[2]].append(rec)
    by_api_j = collections.defaultdict(list)
    for rec in jmps:
        by_api_j[rec[2]].append(rec)

    starts = func_starts(pe)

    # ---- 1) 网络面 ----
    net = [(k, v) for k, v in by_api.items()
           if any(w in k.split('!', 1)[-1] for w in NET_KEY)]
    net.sort(key=lambda kv: (-len(kv[1]), kv[0]))
    print('\n---- 网络面 API 的调用点（def-use 证据） ----')
    if not net:
        print('（无）')
    for k, v in net:
        vs = sorted(set(v))
        print('\n%s   [槽 %s]  %d 个调用点' %
              (k, ', '.join('0x%x' % r for r in sorted(set(r[1] for r in v))), len(vs)))
        for (va, r, lab, sec) in vs:
            ow = owner_of(starts, va)
            print('    call @ 0x%06x  [%s]  func≈0x%06x' %
                  (va, sec, ow if ow else 0))

    # ---- 2) 全部槽的调用点计数（前 40） ----
    if show_all:
        print('\n---- 全部被静态调用的槽（按调用点数排序，前 40） ----')
        rank = sorted(by_api.items(), key=lambda kv: -len(kv[1]))
        for k, v in rank[:40]:
            print('  %4d  %s' % (len(v), k))
    else:
        called = len(by_api)
        print('\n（全部被静态调用的槽 %d 个 / 总槽 %d 个；加 --all 列明细）'
              % (called, len(slots)))

    # ---- 3) 转发桩 ----
    if by_api_j:
        print('\n---- jmp dword ptr [槽]（转发桩，非调用） ----')
        for k in sorted(by_api_j):
            v = by_api_j[k]
            print('  %-40s %d 处: %s' % (k, len(v),
                                        ' '.join('0x%06x' % r[0] for r in sorted(set(v))[:12])))
    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show_all = '--all' in sys.argv
    if not args:
        print(__doc__)
        return
    for p in args:
        try:
            report(p, show_all)
        except Exception as e:
            print('!! %s : %r' % (p, e))


if __name__ == '__main__':
    main()
