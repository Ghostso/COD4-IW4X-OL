import struct, json, os

DUMP = r"D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin"
BASE = 0x400000
d = open(DUMP, "rb").read()

def table(addr, n):
    o = addr - BASE
    out = []
    for i in range(n):
        off, bits, pad = struct.unpack_from("<Iii", d, o + i*12)
        out.append((off, bits, pad))
    return out

PS = table(0xDA8078, 0x57)
ES = table(0xDA63E8, 0x18)
S3 = table(0xDA90A8, 9)

def bits_needed(n):
    return n.bit_length()   # floor(log2(n))+1 == n.bit_length() for n>=1

class Reader:
    """MSG_ReadBits + MSG_ReadBytes with the engine's split cursor."""
    def __init__(self, data, pos=0):
        self.data = data
        self.cursor = pos      # byte cursor
        self.bit = pos * 8     # absolute bit cursor
        self.overflow = False
    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                if self.cursor >= len(self.data):
                    self.overflow = True
                    return 0
                self.bit = self.cursor * 8
                self.cursor += 1
            v |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v
    def bytes_(self, n):
        if self.cursor + n > len(self.data):
            self.overflow = True
            return b"\x00"*n
        b = self.data[self.cursor:self.cursor+n]
        self.cursor += n
        return b
    def bytepos(self):
        return (self.bit + 7) // 8

def decode_run(r, w):
    """0x670CB0"""
    if w == 1:
        n = 0
        while r.bits(1) == 0:
            n += 1
        return n
    if r.bits(1):
        return 1
    mask = (1 << w) - 1
    total = 1
    while True:
        v = r.bits(w)
        total += v
        if v != mask:
            return total

def read_delta_struct(r, table, nfields, from_vals, trace=None, tag=""):
    """0x670FF0 faithful."""
    w = bits_needed(nfields)
    if r.bits(1) == 0:
        # no delta -> read full struct (0x671140): every field, absolute
        out = list(from_vals)
        for i in range(nfields):
            out[i] = read_field(r, table, i, 0)
        return out, "FULL"
    total = r.bits(w)
    if total > nfields:
        r.overflow = True
        return list(from_vals), "OVERFLOW"
    out = list(from_vals)
    last = -1
    while True:
        run = decode_run(r, w)
        end = last + run
        idx = last + 1
        while idx < end:
            out[idx] = read_field(r, table, idx, from_vals[idx])
            idx += 1
        if end < 0 or end >= nfields:
            r.overflow = True
            return out, "OVERFLOW"
        out[end] = read_field(r, table, end, 0)   # absolute
        last = end
        if end == total:
            break
        if end > total:
            r.overflow = True
            return out, "OVERFLOW"
    return out, "DELTA"

def read_field(r, table, idx, base):
    off, bits, pad = table[idx]
    if bits == 0:
        return base
    if bits == -94:
        b = r.bytes_(8)
        return b
    if bits > 0:
        return r.bits(bits)
    # negative codecs: read appropriate raw width (approximate, for trace)
    return ("codec", bits, r.bits(abs(bits) if abs(bits) <= 32 else 32))

if __name__ == "__main__":
    import sys
    hexf = sys.argv[1] if len(sys.argv) > 1 else r"D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/R3_EVIDENCE_20261021_122246/snapshot124/input/reference_124.hex"
    h = open(hexf).read().strip()
    data = bytes.fromhex(h)
    print("file", os.path.basename(hexf), "len", len(data))
    r = Reader(data)
    ack = struct.unpack("<I", r.bytes_(4))[0]
    b5  = r.bytes_(1)[0]
    st  = struct.unpack("<I", r.bytes_(4))[0]
    f1  = r.bytes_(1)[0]
    f2  = r.bytes_(1)[0]
    print("ack=%d b5=%d serverTime=%d flags=%d,%d  cursor=%d" % (ack,b5,st,f1,f2,r.cursor))
    print("next 3 bits:", r.bits(1), r.bits(1), r.bits(8))
    print("bitpos after header bits:", r.bit, "cursor", r.cursor)
    vals, kind = read_delta_struct(r, PS, len(PS), [0]*len(PS))
    print("playerState:", kind, "overflow", r.overflow, "bit", r.bit, "cursor", r.cursor, "bytes", r.bytepos())