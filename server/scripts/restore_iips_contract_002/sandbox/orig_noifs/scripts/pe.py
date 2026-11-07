"""CODOL codoMP_client_shipRetailBase.dll 静态分析公共库。

节表解析已修正：SizeOfOptionalHeader 在 PE+0x14，不在 PE+0x0E。
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')

DLL = r'd:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll'
PE_OFF = 0x110
IMAGE_BASE = 0x10000000


class Image:
    def __init__(self, path=DLL):
        self.data = open(path, 'rb').read()
        d = self.data
        pe = PE_OFF
        self.nsects = struct.unpack_from('<H', d, pe + 6)[0]
        opt_size = struct.unpack_from('<H', d, pe + 20)[0]
        opt = pe + 24
        self.entry, self.base_of_code, _, _ = struct.unpack_from('<IIII', d, opt + 16)
        self.sections = []
        sec_start = opt + opt_size
        for i in range(self.nsects):
            off = sec_start + i * 40
            nm, vs, va, rs, ra, _, _, _, _, fl = struct.unpack_from('<8sIIIIIIHHI', d, off)
            self.sections.append({
                'name': nm.rstrip(b'\x00').decode('latin1'),
                'va': va, 'vsize': vs, 'raw': ra, 'rawsize': rs, 'flags': fl,
            })

    def section_of(self, va):
        for s in self.sections:
            if s['va'] <= va < s['va'] + max(s['vsize'], s['rawsize']):
                return s
        return None

    def foff(self, va):
        s = self.section_of(va)
        if s is None:
            return None
        delta = va - s['va']
        if delta >= s['rawsize']:
            return None          # 在虚拟空洞里（.bss 化），文件里没有
        return s['raw'] + delta

    def voff(self, fo):
        for s in self.sections:
            if s['raw'] <= fo < s['raw'] + s['rawsize']:
                return s['va'] + (fo - s['raw'])
        return None

    def read(self, va, n):
        o = self.foff(va)
        if o is None:
            return None
        return self.data[o:o + n]

    def cstr(self, va, limit=256):
        o = self.foff(va)
        if o is None:
            return None
        e = self.data.find(b'\x00', o)
        if e < 0 or e - o > limit:
            return None
        raw = self.data[o:e]
        try:
            return raw.decode('ascii')
        except UnicodeDecodeError:
            return None

    def xrefs_to_imm32(self, target_va, only_text=True):
        """找 'push imm32' / 'mov reg, imm32' 形式的绝对地址引用。

        返回 (file_offset, va, opcode_bytes) 列表。
        """
        hits = []
        pat = struct.pack('<I', target_va)
        for s in self.sections:
            if only_text and s['name'] != '.text':
                continue
            start, end = s['raw'], s['raw'] + s['rawsize']
            i = self.data.find(pat, start, end)
            while i >= 0:
                hits.append((i, self.voff(i), self.data[i - 1:i + 4]))
                i = self.data.find(pat, i + 1, end)
        return hits


def dump_sections(img):
    print('=== Sections ===')
    for i, s in enumerate(img.sections):
        print(f"  [{i}] {s['name']:10s} va=0x{s['va']:08x} vsize=0x{s['vsize']:07x} "
              f"raw=0x{s['raw']:08x} rawsize=0x{s['rawsize']:07x}")
