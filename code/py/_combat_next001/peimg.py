# -*- coding: utf-8 -*-
"""COMBAT-V0.1-NEXT-001 静态分析基座（只读镜像，不启动/不附加客户端进程）。

用法:
    import sys; sys.path.insert(0, r'<this dir>')
    from peimg import PE
    pe = PE.load()
    pe.dis(0x632680, 40)          # 反汇编
    pe.xrefs_to_imm(0xDC69B0)     # 常量/xref 搜索
"""
import os
import struct

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEFAULT_IMAGE = os.environ.get("CODOL_IMAGE") or os.path.join(
    WORKSPACE, "CODOLServer", "_mainline",
    "_dyn100_run_20260925_182324", "live", "image_best.bin")

SECT_HDR = 40


class Section(object):
    def __init__(self, name, vsize, vaddr, rawsize, rawptr, chars):
        self.name = name
        self.vsize = vsize
        self.vaddr = vaddr
        self.rawsize = rawsize
        self.rawptr = rawptr
        self.chars = chars

    def __repr__(self):
        return "<%s va=%08X vsz=%X raw=%X>" % (
            self.name, self.vaddr, self.vsize, self.rawsize)


class PE(object):
    def __init__(self, data, base):
        self.data = data
        self.base = base
        self.sections = []

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, path=None):
        path = path or DEFAULT_IMAGE
        with open(path, "rb") as f:
            data = f.read()
        if data[0:2] != b"MZ":
            raise ValueError("not MZ")
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
            raise ValueError("not PE at e_lfanew=0x%X" % e_lfanew)
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        if magic == 0x20B:
            image_base = struct.unpack_from("<Q", data, opt + 24)[0]
        else:
            image_base = struct.unpack_from("<I", data, opt + 28)[0]
        sh = opt + opt_size
        pe = cls(data, image_base)
        for i in range(nsec):
            off = sh + i * SECT_HDR
            nm = data[off:off + 8].rstrip(b"\0").decode("latin1")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
            chars = struct.unpack_from("<I", data, off + 36)[0]
            pe.sections.append(Section(nm, vsize, vaddr, rawsize, rawptr, chars))
        return pe

    # ---------------------------------------------------------------- address
    def va_to_off(self, va):
        rva = va - self.base
        for s in self.sections:
            if s.vaddr <= rva < s.vaddr + max(s.vsize, s.rawsize):
                return s.rawptr + (rva - s.vaddr)
        return None

    def off_to_va(self, off):
        for s in self.sections:
            if s.rawptr <= off < s.rawptr + s.rawsize:
                return self.base + s.vaddr + (off - s.rawptr)
        return None

    def read(self, va, n):
        off = self.va_to_off(va)
        if off is None or off + n > len(self.data):
            return None
        return self.data[off:off + n]

    def section_of(self, va):
        for s in self.sections:
            if s.vaddr + self.base <= va < s.vaddr + self.base + max(s.vsize, s.rawsize):
                return s
        return None

    def is_exec(self, va):
        s = self.section_of(va)
        return bool(s and (s.chars & 0x20000000))

    # ---------------------------------------------------------------- search
    def find_bytes(self, pat, start=0, end=None):
        end = len(self.data) if end is None else end
        out = []
        i = self.data.find(pat, start, end)
        while i != -1:
            out.append(i)
            i = self.data.find(pat, i + 1, end)
        return out

    def find_dword(self, value):
        return [(o, self.off_to_va(o)) for o in
                self.find_bytes(struct.pack("<I", value & 0xFFFFFFFF))]

    def find_cstr(self, s):
        b = s.encode("latin1") if not isinstance(s, bytes) else s
        return [(o, self.off_to_va(o)) for o in self.find_bytes(b)]

    def xrefs_push(self, imm):
        """所有 68 <imm32> 与直接 5 字节 call/jmp (E8/E9 <rel>) 指向 imm 的位置。"""
        out = []
        for o in self.find_bytes(b"\x68" + struct.pack("<I", imm & 0xFFFFFFFF)):
            va = self.off_to_va(o)
            if va and self.is_exec(va):
                out.append(("push", va))
        for o in self.find_bytes(struct.pack("<I", imm & 0xFFFFFFFF)):
            pass
        return out

    def xrefs_to_addr(self, addr):
        """查找把 addr 当作立即数加载/比较/引用（push imm32 / mov reg,imm32 / cmp）的位置。

        只返回位于可执行段内的命中，并带上指令字节以便人工判定。"""
        res = []
        pats = [(b"\x68", "push"), (b"\xb8", "mov eax"), (b"\xb9", "mov ecx"),
                (b"\xba", "mov edx"), (b"\xbb", "mov ebx"), (b"\xbe", "mov esi"),
                (b"\xbf", "mov edi"), (b"\xbd", "mov ebp")]
        for pre, kind in pats:
            for o in self.find_bytes(pre + struct.pack("<I", addr & 0xFFFFFFFF)):
                va = self.off_to_va(o)
                if va and self.is_exec(va):
                    res.append((kind, va))
        # 直接 call/jmp rel32 目标
        for o in self.find_bytes(b"\xe8"):
            if o + 5 > len(self.data):
                continue
            rel = struct.unpack_from("<i", self.data, o + 1)[0]
            va = self.off_to_va(o)
            if va and self.is_exec(va) and va + 5 + rel == addr:
                res.append(("call", va))
        for o in self.find_bytes(b"\xe9"):
            if o + 5 > len(self.data):
                continue
            rel = struct.unpack_from("<i", self.data, o + 1)[0]
            va = self.off_to_va(o)
            if va and self.is_exec(va) and va + 5 + rel == addr:
                res.append(("jmp", va))
        return res

    def calls_to(self, target):
        """所有直接 call target 的位置（E8 rel32）。"""
        out = []
        for o in self.find_bytes(b"\xe8"):
            if o + 5 > len(self.data):
                continue
            rel = struct.unpack_from("<i", self.data, o + 1)[0]
            va = self.off_to_va(o)
            if va and self.is_exec(va) and va + 5 + rel == target:
                out.append(va)
        return out

    # ---------------------------------------------------------------- disasm
    def _md(self):
        try:
            import capstone
        except ImportError:
            return None
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.detail = True
        return md

    def dis(self, va, count=30, to_file=None):
        md = self._md()
        if md is None:
            return ["(capstone unavailable)"]
        n = 0
        out = []
        code = self.data[va - self.base:] if self.section_of(va) else b""
        for ins in md.disasm(code, va):
            line = "%08X  %-24s %s %s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            out.append(line)
            n += 1
            if n >= count:
                break
        if to_file:
            with open(to_file, "w", encoding="utf-8") as f:
                f.write("\n".join(out))
        return out

    def dis_until_ret(self, va, maxn=200):
        md = self._md()
        if md is None:
            return ["(capstone unavailable)"]
        out = []
        code = self.data[va - self.base:]
        for ins in md.disasm(code, va):
            out.append("%08X  %-24s %s %s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            if ins.mnemonic in ("ret", "retn") or len(out) >= maxn:
                break
        return out


def main():
    import sys
    pe = PE.load(sys.argv[1] if len(sys.argv) > 1 else None)
    print("image base = 0x%08X" % pe.base)
    for s in pe.sections:
        print("  ", s)
    for anchor in (0x632680, 0x632462, 0x621E50, 0x7F1540):
        print("anchor 0x%X in exec=%s" % (anchor, pe.is_exec(anchor)))


if __name__ == "__main__":
    main()
