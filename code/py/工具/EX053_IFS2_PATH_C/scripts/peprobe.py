# -*- coding: utf-8 -*-
"""CODOL PE 探针（**只读**）。用于补齐 netmods.txt 的五条覆盖漏洞。

用法：
    python scripts/peprobe.py dirs  <pe>            # 16 个数据目录
    python scripts/peprobe.py imps  <pe>            # dir1 静态导入 + dir13 延迟导入（全量，不截断）
    python scripts/peprobe.py secs  <pe>            # 节表 + 文件偏移<->RVA 换算表
    python scripts/peprobe.py refs  <pe> <substr>   # 找字符串出现处，并扫"指向它的指针"
                                                    # 同时扫 RVA 形式与 VA(ImageBase+RVA) 形式
    python scripts/peprobe.py slots <pe> [<substr>] # 列 IAT 槽（RVA/VA/dll!func）
    python scripts/peprobe.py callers <pe> <子串> [--func]
                                                    # **def-use**：导入名 -> IAT 槽 -> 真实引用点
                                                    # 会标出 call dword ptr [VA] 与仅取地址的区别
    python scripts/peprobe.py xref  <pe> <VA>       # 给定绝对 VA 列出所有引用点（主 EXE 的
                                                    # .idata2 槽用这条，因为 dir1 不可用）
    python scripts/peprobe.py hex   <pe> <rva> <n>  # 按 RVA dump 字节
    python scripts/peprobe.py scan  <pe> <hexbytes> # 全文件原始字节扫描

铁律（本脚本遵守）：
  * 地址一律 **RVA**；只有扫指针时才同时试 RVA / VA 两种形式并明确标注。
  * 不修改任何文件；只 open(...,'rb')。
  * dir1 与 dir13 都解析 —— 只扫 dir1 会整片漏。
  * 序号导入（高位 1<<31）标 ORD#，不做 cstr。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class PE(object):
    MAXDESC = 8192
    MAXTHUNK = 200000

    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        head = self.f.read(0x400)
        if len(head) < 0x40 or head[:2] != b'MZ':
            raise ValueError('no MZ')
        pe = struct.unpack_from('<I', head, 0x3c)[0]
        if pe + 0x18 > len(head):
            self.f.seek(0)
            head = self.f.read(pe + 0x400)
        if head[pe:pe + 4] != b'PE\0\0':
            raise ValueError('no PE')
        self.pe = pe
        self.fsize = os.path.getsize(path)
        nsec, = struct.unpack_from('<H', head, pe + 6)
        optsz, = struct.unpack_from('<H', head, pe + 0x14)
        self.ts, = struct.unpack_from('<I', head, pe + 8)
        opt = pe + 0x18
        magic, = struct.unpack_from('<H', head, opt)
        self.is64 = (magic == 0x20b)
        if magic not in (0x10b, 0x20b):
            raise ValueError('bad magic 0x%x' % magic)
        self.machine, = struct.unpack_from('<H', head, pe + 4)
        self.subsys, = struct.unpack_from('<H', head, opt + 0x44)
        if self.is64:
            self.imagebase, = struct.unpack_from('<Q', head, opt + 0x18)
            self.entry, = struct.unpack_from('<I', head, opt + 0x10)
            self.sizeimage, = struct.unpack_from('<I', head, opt + 0x38)
            self.namedir, = struct.unpack_from('<I', head, opt + 0x6c)
            dd = opt + 0x70
        else:
            self.imagebase, = struct.unpack_from('<I', head, opt + 0x1c)
            self.entry, = struct.unpack_from('<I', head, opt + 0x10)
            self.sizeimage, = struct.unpack_from('<I', head, opt + 0x38)
            self.namedir, = struct.unpack_from('<I', head, opt + 0x5c)
            dd = opt + 0x60
        self.dd = []
        for i in range(min(self.namedir, 16)):
            self.dd.append(struct.unpack_from('<II', head, dd + i * 8))
        sp = pe + 0x18 + optsz
        self.f.seek(sp)
        raw = self.f.read(nsec * 40)
        self.secs = []
        for i in range(nsec):
            o = i * 40
            nm = raw[o:o + 8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, roff = struct.unpack_from('<IIII', raw, o + 8)
            ch, = struct.unpack_from('<I', raw, o + 36)
            self.secs.append((nm, va, vsz, roff, rsz, ch))

    # ---------- 换算 ----------
    def off(self, rva):
        for nm, va, vsz, roff, rsz, ch in self.secs:
            if va <= rva < va + max(vsz, rsz):
                o = roff + (rva - va)
                return o if o < roff + rsz else None
        return None

    def rva_of(self, off):
        for nm, va, vsz, roff, rsz, ch in self.secs:
            if roff <= off < roff + rsz:
                return va + (off - roff)
        return None

    def sec_of(self, off):
        for i, (nm, va, vsz, roff, rsz, ch) in enumerate(self.secs):
            if roff <= off < roff + rsz:
                return i, nm
        return None, None

    def rd(self, rva, n):
        o = self.off(rva)
        if o is None:
            return None
        self.f.seek(o)
        return self.f.read(n)

    def cstr_rva(self, rva, n=256):
        b = self.rd(rva, n)
        if b is None:
            return None
        z = b.find(b'\0')
        return b[:z if z >= 0 else len(b)].decode('latin1', 'replace')

    def cstr_off(self, off, n=256):
        self.f.seek(off)
        b = self.f.read(n)
        z = b.find(b'\0')
        return b[:z if z >= 0 else len(b)].decode('latin1', 'replace')

    # ---------- 导入 ----------
    def thunk_names(self, ilt_rva):
        funcs = []
        if not ilt_rva:
            return funcs
        w = 8 if self.is64 else 4
        hi = 1 << (63 if self.is64 else 31)
        for i in range(self.MAXTHUNK):
            b = self.rd(ilt_rva + i * w, w)
            if not b or len(b) < w:
                break
            v = struct.unpack_from('<Q' if self.is64 else '<I', b)[0]
            if v == 0:
                break
            if v & hi:
                funcs.append('ORD#%d' % (v & 0xffff))
            else:
                s = self.cstr_rva(v + 2, 128)
                funcs.append(s if s else '?')
        return funcs

    def import_descs(self):
        if not self.dd[1][0]:
            return []
        out = []
        o = self.off(self.dd[1][0])
        if o is None:
            return out
        for i in range(self.MAXDESC):
            self.f.seek(o + i * 20)
            b = self.f.read(20)
            if len(b) < 20:
                break
            oft, ts, fc, name_rva, ft = struct.unpack('<IIIII', b)
            if oft == 0 and name_rva == 0 and ft == 0:
                break
            out.append((self.cstr_rva(name_rva) if name_rva else None,
                        self.thunk_names(oft or ft), i))
        return out

    def delay_descs(self):
        if len(self.dd) < 14 or not self.dd[13][0]:
            return []
        out = []
        o = self.off(self.dd[13][0])
        if o is None:
            return out
        for i in range(self.MAXDESC):
            self.f.seek(o + i * 32)
            b = self.f.read(32)
            if len(b) < 32:
                break
            attrs, name, hmod, iat, int_, biat, uiat, ts = struct.unpack('<IIIIIIII', b)
            if attrs == 0 and name == 0 and iat == 0:
                break
            if attrs & 1:
                nr, ir = name, int_
            else:
                nr = (name - self.imagebase) if name else 0
                ir = (int_ - self.imagebase) if int_ else 0
            out.append((attrs, self.cstr_rva(nr) if nr else None,
                        self.thunk_names(ir), iat, ir, i))
        return out


def do_dirs(pe):
    print('文件 %s  (%d 字节)' % (pe.path, pe.fsize))
    print('Machine=0x%04x  PE32%s  ImageBase=0x%08x  EntryPoint(RVA)=0x%x'
          % (pe.machine, '+' if pe.is64 else '', pe.imagebase, pe.entry))
    print('SizeOfImage=0x%x  Subsystem=%d  TimeDateStamp=0x%08x  nDir=%d'
          % (pe.sizeimage, pe.subsys, pe.ts, pe.namedir))
    names = ['EXPORT', 'IMPORT', 'RESOURCE', 'EXCEPTION', 'SECURITY', 'BASERELOC',
             'DEBUG', 'ARCH', 'GLOBALPTR', 'TLS', 'LOADCONFIG', 'BOUNDIMPORT',
             'IAT', 'DELAYIMPORT', 'CLR', 'RESERVED']
    for i, (rva, sz) in enumerate(pe.dd):
        print('  [%2d] %-12s rva=0x%08x  size=0x%x' % (i, names[i], rva, sz))
    # dir12 IAT 范围 + dir0 导出
    if pe.dd[12][0]:
        print('  IAT: rva 0x%x .. 0x%x  (%d 槽 @4B)'
              % (pe.dd[12][0], pe.dd[12][0] + pe.dd[12][1], pe.dd[12][1] // 4))


def do_secs(pe):
    for i, (nm, va, vsz, roff, rsz, ch) in enumerate(pe.secs):
        print('[%d] %-9s va=0x%08x vsz=0x%08x raw=0x%08x rsz=0x%08x ch=0x%08x'
              % (i, nm, va, vsz, roff, rsz, ch))
        d = 0 if va == roff else (va - roff)
        print('     文件偏移 0x%x..0x%x  <=>  RVA 0x%x..0x%x  (RVA = off %+d)'
              % (roff, roff + rsz, va, va + rsz, d))


def do_imps(pe):
    print('=== dir1 静态导入 (rva=0x%x size=0x%x)' % pe.dd[1])
    ds = pe.import_descs()
    print('描述符 %d 个' % len(ds))
    for nm, fx, i in ds:
        print('\n[%d] %s   n=%d' % (i, nm, len(fx)))
        print('    %s' % ' '.join(fx))
    print('\n=== dir12 IAT rva=0x%x size=0x%x' % pe.dd[12])
    print('=== dir13 延迟导入 (rva=0x%x size=0x%x)' % pe.dd[13])
    dl = pe.delay_descs()
    print('延迟描述符 %d 个' % len(dl))
    for attrs, nm, fx, iat, ilt, i in dl:
        print('\n[%d] attrs=0x%x %s   IAT_rva=0x%x ILT_rva=0x%x  n=%d'
              % (i, attrs, nm, iat, ilt, len(fx)))
        print('    %s' % ' '.join(fx))


def sec_tail(sn):
    """给落点加一句形态提示：.rdata 里的指针通常是 RTTI 类型描述符 / vftable。"""
    if sn == '.rdata':
        return '   << .rdata(常见 RTTI TypeDescriptor / vftable)'
    if sn and sn.startswith('.text'):
        return '   << .text(代码引用)'
    return ''


def str_start(blob, k, back=512):
    """从命中偏移回溯到所在 **NUL 分隔串的首字节**。

    为什么必须这样：RTTI 类名在文件里的存储形态是 `.?AVdwLobbyEventHandler@@`，
    裸名 `dwLobbyEventHandler` 只是它内部的一个子串（偏移 +4）。
    代码/数据里引用的指针指向的是**整条串的首字节**（那个 `.`），不是子串那个 `d`。
    只扫「指向子串自身」的指针 ⇒ 必然 0 命中 ⇒ 会把真实存在的东西误判成「作废」。
    """
    lo = max(0, k - back)
    z = blob.rfind(b'\0', lo, k)
    return (z + 1) if z >= 0 else k


def do_refs(pe, needle):
    nb = needle.encode('latin1')
    self_blob = None
    with open(pe.path, 'rb') as g:
        self_blob = g.read()
    hits = []
    st = 0
    while True:
        k = self_blob.find(nb, st)
        if k < 0:
            break
        hits.append(k)
        st = k + 1
    print('字符串 %r 在文件中出现 %d 次' % (needle, len(hits)))
    for k in hits:
        rva = pe.rva_of(k)
        si, sn = pe.sec_of(k)
        print('  off=0x%-8x rva=%s sec=[%s]%s  文本=%r'
              % (k, ('0x%08x' % rva) if rva is not None else 'N/A',
                 si, sn, pe.cstr_off(k, 96)))
    # 扫指针。两遍：先「指向子串自身」，再「指向所在 NUL 串首」。
    # 第二遍才是 RTTI / 符号表的正确问法（见 str_start 的说明）。
    for k in hits:
        rva = pe.rva_of(k)
        if rva is None:
            continue
        ss = str_start(self_blob, k)
        srva = pe.rva_of(ss)
        if ss != k and srva is not None:
            print('\n--- 指向**所在 NUL 串首**的指针 (串首 off=0x%x rva=0x%x) ---'
                  % (ss, srva))
            print('    串首内容 = %r' % pe.cstr_off(ss, 96))
            for label, val in (('VA', pe.imagebase + srva), ('RVA', srva)):
                pat = struct.pack('<I' if not pe.is64 else '<Q', val)
                st = 0
                n = 0
                while True:
                    j = self_blob.find(pat, st)
                    if j < 0:
                        break
                    n += 1
                    jr = pe.rva_of(j)
                    si, sn = pe.sec_of(j)
                    op, _instr = classify_ref(self_blob, j)
                    print('  %s 0x%08x -> off=0x%-8x rva=%-12s sec=[%s]%s  %s%s'
                          % (label, val, j, ('0x%08x' % jr) if jr is not None else 'N/A',
                             si, sn, op, sec_tail(sn)))
                    st = j + 1
                    if n > 40:
                        print('  ...(截断)')
                        break
                if n == 0:
                    print('  %s 0x%08x -> 0 个引用' % (label, val))
        print('\n--- 指向**命中子串自身**的指针 (off=0x%x rva=0x%x) ---' % (k, rva))
        for label, val in (('VA', pe.imagebase + rva), ('RVA', rva)):
            pat = struct.pack('<I' if not pe.is64 else '<Q', val)
            st = 0
            n = 0
            while True:
                j = self_blob.find(pat, st)
                if j < 0:
                    break
                n += 1
                jr = pe.rva_of(j)
                si, sn = pe.sec_of(j)
                op, _instr = classify_ref(self_blob, j)
                print('  %s 0x%08x -> off=0x%-8x rva=%-12s sec=[%s]%s  %s%s'
                      % (label, val, j, ('0x%08x' % jr) if jr is not None else 'N/A',
                         si, sn, op, sec_tail(sn)))
                st = j + 1
                if n > 40:
                    print('  ...(截断)')
                    break
            if n == 0:
                print('  %s 0x%08x -> 0 个引用' % (label, val))


# ---------- def-use：IAT 槽 -> 真实调用点 ----------

def build_iat_map(pe):
    """{IAT槽RVA: 'dll!func'}。

    槽 RVA 取 **FirstThunk**（ft）基址，因为运行期代码引用的正是这一列；
    ILT(oft) 只在没被 bound 时才有名字。只扫 dir1 会整片漏。
    """
    m = {}
    if not pe.dd[1][0]:
        return m
    o = pe.off(pe.dd[1][0])
    if o is None:
        return m
    w = 8 if pe.is64 else 4
    hi = 1 << (63 if pe.is64 else 31)
    for i in range(pe.MAXDESC):
        pe.f.seek(o + i * 20)
        b = pe.f.read(20)
        if len(b) < 20:
            break
        oft, ts, fc, name_rva, ft = struct.unpack('<IIIII', b)
        if oft == 0 and name_rva == 0 and ft == 0:
            break
        dll = pe.cstr_rva(name_rva) if name_rva else '?'
        ilt = oft or ft
        if not ilt or not ft:
            continue
        for j in range(pe.MAXTHUNK):
            rb = pe.rd(ilt + j * w, w)
            if not rb or len(rb) < w:
                break
            v = struct.unpack_from('<Q' if pe.is64 else '<I', rb)[0]
            if v == 0:
                break
            if v & hi:
                fn = 'ORD#%d' % (v & 0xffff)
            else:
                fn = pe.cstr_rva(v + 2, 128) or '?'
            m[ft + j * w] = '%s!%s' % (dll, fn)
    return m


# 反向判形态：看「指针字节」之前 1~2 字节是什么操作码。
# 关键一条是 FF 15 —— call dword ptr [VA]，那才是**真实 def-use**；
# 其余 push/mov 只能证明「取过地址」，不证明调用。
_ABS_FORMS = {
    (0xff, 0x15): 'call dword ptr [VA]',
    (0xff, 0x25): 'jmp  dword ptr [VA]',
    (0xff, 0x05): 'inc  dword ptr [VA]',
    (0xff, 0x0d): 'dec  dword ptr [VA]',
    (0x8b, 0x05): 'mov  eax, [VA]',
    (0x8b, 0x0d): 'mov  ecx, [VA]',
    (0x8b, 0x15): 'mov  edx, [VA]',
    (0x8b, 0x1d): 'mov  ebx, [VA]',
    (0x8b, 0x35): 'mov  esi, [VA]',
    (0x8b, 0x3d): 'mov  edi, [VA]',
    (0x89, 0x05): 'mov  [VA], eax',
    (0x89, 0x0d): 'mov  [VA], ecx',
    (0x89, 0x15): 'mov  [VA], edx',
    (0x39, 0x05): 'cmp  [VA], eax',
    (0x3b, 0x05): 'cmp  eax, [VA]',
    (0x68,): 'push VA (取地址)',
    (0xa1,): 'mov  eax, [VA]',
    (0xa3,): 'mov  [VA], eax',
}


def classify_ref(blob, poff):
    """poff = 指针字节起始文件偏移。返回 (形态, 指令起始偏移)。"""
    for n in (2, 1):
        if poff - n < 0:
            continue
        key = tuple(blob[poff - n:poff])
        if key in _ABS_FORMS:
            return _ABS_FORMS[key], poff - n
    return '?(未知/数据)', poff


def refs_to_va(pe, blob, va, cap=400):
    w = 8 if pe.is64 else 4
    pat = struct.pack('<Q' if pe.is64 else '<I', va)
    out = []
    st = 0
    while True:
        j = blob.find(pat, st)
        if j < 0:
            break
        out.append(j)
        st = j + 1
        if len(out) >= cap:
            break
    return out


def _func_starts(pe):
    """轻量函数入口启发式（32 位）：E8 rel32 落点 + 典型 prologue。

    只为把调用点归属到一个近似函数头，**不是**真函数边界。
    """
    starts = set()
    for nm, va, vsz, roff, rsz, ch in pe.secs:
        if not (ch & 0x20000000):        # 非可执行节，跳
            continue
        # E8 rel32 落点
        pe.f.seek(roff)
        blk = pe.f.read(rsz)
        k = blk.find(b'\xe8')
        while k >= 0:
            if k + 5 <= len(blk):
                rel, = struct.unpack_from('<i', blk, k + 1)
                tgt = va + k + 5 + rel
                if tgt >= va:
                    starts.add(tgt)
            k = blk.find(b'\xe8', k + 1)
        for p in (b'\x55\x8b\xec', b'\x8b\xff\x55\x8b\xec', b'\x6a\xff\x68'):
            k = blk.find(p)
            while k >= 0:
                starts.add(va + k)
                k = blk.find(p, k + 1)
    return sorted(starts)


def _owner(starts, rva):
    import bisect
    i = bisect.bisect_right(starts, rva) - 1
    return starts[i] if i >= 0 else None


def do_callers(pe, needle, want_func=False, cap=400):
    """把导入名解析到 IAT 槽，再找**代码里真实引用该槽**的点。"""
    blob = open(pe.path, 'rb').read()
    m = build_iat_map(pe)
    print('文件 %s' % pe.path)
    print('dir1 解析出 IAT 槽 %d 个' % len(m))
    if not m:
        print('!! dir1 无导入表。主 EXE 的 IAT 是非标准 .idata2，本命令不适用；')
        print('   改用：peprobe.py xref <pe> <槽VA>   （VA 由 importmap.py 给出）')
        return None
    nl = needle.lower()
    sel = [(s, l) for s, l in sorted(m.items()) if nl in l.lower()]
    if not sel:
        print('没有导入名匹配 %r。可先跑 imps 看全量名面。' % needle)
        return None
    starts = _func_starts(pe) if want_func else None
    for slot, lab in sel:
        va = pe.imagebase + slot
        hits = refs_to_va(pe, blob, va, cap)
        code, data = [], []
        for j in hits:
            op, instr = classify_ref(blob, j)
            jr = pe.rva_of(j)
            si, sn = pe.sec_of(j)
            rec = (instr, j, jr, si, sn, op)
            if sn and sn.startswith('.text'):
                code.append(rec)
            else:
                data.append(rec)
        print('\n=== %s   槽RVA=0x%x  槽VA=0x%08x' % (lab, slot, va))
        print('    引用 %d 处：可执行 %d / 数据 %d' % (len(hits), len(code), len(data)))
        for tag, bucket in (('CODE', code), ('DATA', data)):
            for instr, j, jr, si, sn, op in bucket:
                extra = ''
                if tag == 'CODE' and starts:
                    o = _owner(starts, jr)
                    if o is not None:
                        extra = '  func~0x%x' % o
                print('    %-4s off=0x%-8x rva=%-12s [%s]%s  %-22s instr@0x%x%s'
                      % (tag, j, ('0x%08x' % jr) if jr is not None else 'N/A',
                         si, sn, op, instr, extra))
        real = [r for r in code if r[5].startswith('call')]
        if real:
            print('    >> **%d 处真实 call [VA]** ⇒ def-use 成立' % len(real))
        else:
            print('    >> 无可执行段 call [VA] ⇒ 静态未见真实调用'
                  '（导入但未被调用，或只被取地址）')
    return sel


def do_xref(pe, va):
    """给定绝对 VA（例如 IAT 槽 VA），列出所有引用点。"""
    blob = open(pe.path, 'rb').read()
    m = build_iat_map(pe)
    lab = ''
    if pe.imagebase <= va < pe.imagebase + pe.sizeimage:
        s = m.get(va - pe.imagebase)
        if s:
            lab = '   = IAT槽: %s' % s
    hits = refs_to_va(pe, blob, va)
    print('VA 0x%08x%s' % (va, lab))
    print('引用 %d 处' % len(hits))
    for j in hits:
        op, instr = classify_ref(blob, j)
        jr = pe.rva_of(j)
        si, sn = pe.sec_of(j)
        print('    off=0x%-8x rva=%-12s [%s]%s  %-22s instr@0x%x'
              % (j, ('0x%08x' % jr) if jr is not None else 'N/A', si, sn, op, instr))
    return hits


def do_slots(pe, needle=None):
    """列出 IAT 槽（RVA/VA/dll!func），便于接着喂给 xref。"""
    m = build_iat_map(pe)
    print('IAT 槽 %d 个' % len(m))
    nl = (needle or '').lower()
    for slot, lab in sorted(m.items()):
        if nl and nl not in lab.lower():
            continue
        print('    slotRVA=0x%-10x slotVA=0x%08x  %s' % (slot, pe.imagebase + slot, lab))


def do_hex(pe, rva, n):
    b = pe.rd(rva, n)
    if b is None:
        print('RVA 0x%x 不在任何节内' % rva)
        return
    for i in range(0, len(b), 16):
        chunk = b[i:i + 16]
        print('%08x  %-47s  %s' % (rva + i,
                                   ' '.join('%02x' % c for c in chunk),
                                   ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)))


def do_scan(pe, hexs):
    pat = bytes.fromhex(hexs)
    with open(pe.path, 'rb') as g:
        blob = g.read()
    st = 0
    cnt = 0
    while True:
        j = blob.find(pat, st)
        if j < 0:
            break
        cnt += 1
        rva = pe.rva_of(j)
        si, sn = pe.sec_of(j)
        print('  off=0x%-8x rva=%-12s sec=[%s]%s' % (j, ('0x%08x' % rva) if rva is not None else 'N/A', si, sn))
        st = j + 1
        if cnt > 300:
            print('  ...(截断)')
            break
    print('共 %d 处' % cnt)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, path = sys.argv[1], sys.argv[2]
    pe = PE(path)
    if cmd == 'dirs':
        do_dirs(pe)
    elif cmd == 'secs':
        do_secs(pe)
    elif cmd == 'imps':
        do_imps(pe)
    elif cmd == 'refs':
        do_refs(pe, sys.argv[3])
    elif cmd == 'slots':
        do_slots(pe, sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == 'callers':
        # callers <pe> <导入名子串> [--func]
        do_callers(pe, sys.argv[3],
                   want_func='--func' in sys.argv)
    elif cmd == 'xref':
        do_xref(pe, int(sys.argv[3], 16))
    elif cmd == 'hex':
        do_hex(pe, int(sys.argv[3], 16), int(sys.argv[4]) if len(sys.argv) > 4 else 256)
    elif cmd == 'scan':
        do_scan(pe, sys.argv[3])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
