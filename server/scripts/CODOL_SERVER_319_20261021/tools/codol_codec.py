
"""CODOL 3.19 in-match delta codec - faithful to 0x670FF0 / 0x670CB0 / 0x6701D0 / 0x676E00 / 0x6779B0 / 0x677E10."""
import struct

DUMP = r"D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
BASE = 0x400000
_d = open(DUMP, "rb").read()

def load_table(addr, n):
    o = addr - BASE
    return [struct.unpack_from("<Iii", _d, o + i * 12) for i in range(n)]

TABLES = {
    "playerState":   (0xDA8078, 87),
    "entityState":   (0xDA63E8, 24),
    "struct3":       (0xDA90A8, 9),
    "subStruct":     (0xDA9138, 42),
    "bigStruct":     (0xDA8520, 246),
}

# 0xDA9330: array-element type id -> netField table pointer.
# Every layout has max_index=0x3F, i.e. 64 records (indices 0..63).
ARRAY_ELEMENT_TYPE_ADDRESSES = (
    0xDA4608,  # 0
    0xDA4BF8,  # 1
    0xDA4EF0,  # 2
    0xDA6508,  # 3
    0xDA7A20,  # 4
    0xDA4608,  # 5
    0xDA6808,  # 6
    0xDA6E08,  # 7
    0xDA7108,  # 8
    0xDA7408,  # 9
    0xDA7728,  # 10
    0xDA4608,  # 11
    0xDA5AF0,  # 12
    0xDA54E0,  # 13
    0xDA57D8,  # 14
    0xDA51E8,  # 15
    0xDA4608,  # 16
    0xDA4608,  # 17
    0xDA4608,  # 18
    0xDA5DE8,  # 19
    0xDA4608,  # 20
    0xDA60E8,  # 21
    0xDA6B08,  # 22
    0xDA4900,  # 23
)

TABLES.update(
    {f"arrayElemType{type_id}": (address, 64)
     for type_id, address in enumerate(ARRAY_ELEMENT_TYPE_ADDRESSES)}
)

def index_bits(n):
    """Bits needed to encode max index n-1 (64 entries -> 6 bits)."""
    return max(1, (n - 1).bit_length())

# ---------------------------------------------------------------- writer
class BitWriter:
    """Mirrors engine MSG_WriteBits: LSB-first, byte-aligned start."""
    def __init__(self):
        self.data = bytearray()
        self.bit = 0
    def bits(self, v, n):
        for i in range(n):
            if (self.bit & 7) == 0:
                self.bit = len(self.data) * 8
                self.data.append(0)
            self.data[self.bit >> 3] |= ((v >> i) & 1) << (self.bit & 7)
            self.bit += 1
    def bytes_(self, b):
        self.data += bytes(b)

class BitReader:
    def __init__(self, data):
        self.data = data
        self.cursor = 0
        self.bit = 0
        self.ovf = False
    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                if self.cursor >= len(self.data):
                    self.ovf = True
                    return 0
                self.bit = self.cursor * 8
                self.cursor += 1
            v |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v
    def bytes_(self, n):
        if self.cursor + n > len(self.data):
            self.ovf = True
            return b"\x00" * n
        b = self.data[self.cursor:self.cursor + n]
        self.cursor += n
        return b

# ---------------------------------------------------------------- index varint
def w_run(w, run, ib):
    """0x670CB0 inverse."""
    if ib == 1:
        for _ in range(run):
            w.bits(1, 1)
        w.bits(0, 1)
        return
    if run == 1:
        w.bits(1, 1)
        return
    w.bits(0, 1)
    left = run - 1
    mask = (1 << ib) - 1
    while left >= mask:
        w.bits(mask, ib)
        left -= mask
    w.bits(left, ib)

def r_run(r, ib):
    if ib == 1:
        n = 0
        while r.bits(1):
            n += 1
        return n
    if r.bits(1):
        return 1
    mask = (1 << ib) - 1
    n = 1
    while True:
        v = r.bits(ib)
        n += v
        if v != mask:
            return n

# ---------------------------------------------------------------- field codec
KNOWN_CODECS = set(range(-65, -54)) | set(range(-102, -68))

def field_width(bits):
    """Return ('u',n) unsigned, ('s',n) signed, ('z',0) unused, ('c',codec) special."""
    if bits == 0: return ("f", 0)
    if bits > 0:  return ("u", bits)
    if bits in KNOWN_CODECS: return ("c", bits)
    return ("s", -bits)      # negative non-codec = signed integer

def w_field(w, bits, to, frm):
    kind, n = field_width(bits)
    if kind == "f":
        fb = struct.unpack("<I", struct.pack("<f", float(to)))[0]
        nb = struct.unpack("<I", struct.pack("<f", float(frm)))[0]
        if fb == 0:
            w.bits(0, 1); w.bits(0, 1)
        elif fb == 0x80000000:
            w.bits(0, 1); w.bits(1, 1)
        else:
            w.bits(1, 1); w.bits(1, 1); w.bytes_(struct.pack("<I", fb ^ nb))
        return
    if kind == "u":
        w.bits(0 if to == 0 else 1, 1)
        if to: w.bits(to ^ frm, n)
        return
    if kind == "s":
        w.bits(0 if to == 0 else 1, 1)
        if to: w.bits((to ^ frm) & ((1 << n) - 1), n)
        return
    # codec: minimal support for the ones our 6 tables need
    c = n
    if c == -94:
        w.bytes_(bytes(to))
    elif c == -97:
        d = (frm - to) & 0xFFFFFFFF
        if d == 0:
            w.bits(1, 1); w.bytes_(struct.pack("<I", to & 0xFFFFFFFF))
        else:
            w.bits(0, 1); w.bits(d & 0xFF, 8)
    elif c == -57:
        v = int(round(to * 65536.0 / 360.0)) & 0xFFFF
        w.bytes_(struct.pack("<H", v))
    else:
        raise NotImplementedError("codec %d" % c)

def r_field(r, bits, frm):
    kind, n = field_width(bits)
    if kind == "f":
        if r.bits(1) == 0:
            return struct.unpack("<f", struct.pack("<I", r.bits(1) << 31))[0]
        if r.bits(1) == 1:
            raw = struct.unpack("<I", r.bytes_(4))[0]
            return struct.unpack("<f", struct.pack("<I", raw ^ struct.unpack("<I", struct.pack("<f", float(frm)))[0]))[0]
        raise NotImplementedError("float compressed")
    if kind in ("u", "s"):
        if r.bits(1) == 0: return 0
        v = r.bits(n) ^ (frm & ((1 << n) - 1))
        if kind == "s" and n and (v >> (n - 1)) & 1:
            v -= (1 << n)
        return v
    c = n
    if c == -94:
        return r.bytes_(8)
    if c == -97:
        if r.bits(1) == 0:
            return (frm - r.bits(8)) & 0xFFFFFFFF
        return struct.unpack("<I", r.bytes_(4))[0]
    if c == -57:
        v = struct.unpack("<H", r.bytes_(2))[0]
        return v * 360.0 / 65536.0
    raise NotImplementedError("codec %d" % c)

# ---------------------------------------------------------------- struct delta
def w_struct(w, table, to, frm, absolute=False):
    """Mirror 0x677E10: has-delta + lastChanged + runs."""
    n = len(table)
    ib = index_bits(n)
    if absolute:
        w.bits(0, 1)
        for i in range(n):
            w_field(w, table[i][1], to[i], 0)
        return
    last = -1
    for i in range(n - 1, -1, -1):
        if to[i] != frm[i]:
            last = i
            break
    if last < 0:
        w.bits(0, 1)
        for i in range(n):
            w_field(w, table[i][1], to[i], frm[i])
        return
    w.bits(1, 1)
    w.bits(last, ib)
    prev = -1
    for i in range(last + 1):
        changed = (to[i] != frm[i])
        if changed:
            w_run(w, i - prev, ib)
            w_field(w, table[i][1], to[i], frm[i])
            prev = i
    return

def r_struct(r, table, frm):
    n = len(table)
    ib = index_bits(n)
    out = list(frm)
    if r.bits(1) == 0:
        for i in range(n):
            out[i] = r_field(r, table[i][1], 0)
        return out
    total = r.bits(ib)
    if total >= n:
        r.ovf = True
        return out
    last = -1
    while True:
        idx = last + r_run(r, ib)
        for i in range(last + 1, idx):
            out[i] = frm[i]
        if idx >= n:
            r.ovf = True
            return out
        out[idx] = r_field(r, table[idx][1], frm[idx])
        last = idx
        if idx == total:
            break
    return out
