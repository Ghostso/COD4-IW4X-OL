import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from codol_snapshot_codec import BitWriter

class Reader:
    def __init__(self, data):
        self.data = data
        self.bit = 0
        self.cursor = 0
    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                self.bit = self.cursor * 8
                self.cursor += 1
            v |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v

def read_run(r, index_bits):
    if r.bits(1) == 1:
        return 1
    mask = (1 << index_bits) - 1
    run = 1
    while True:
        v = r.bits(index_bits)
        run += v
        if v != mask:
            return run

def main():
    for bits in (4, 5, 6, 7, 8):
        for run in (1, 2, 14, 15, 16, 127, 128, (1 << bits) - 1, 1 << bits):
            w = BitWriter()
            w.run(run, bits)
            got = read_run(Reader(bytes(w.data)), bits)
            assert got == run, (bits, run, got, w.data.hex())
    print("snapshot run codec: all checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
