# -*- coding: utf-8 -*-
"""S2-E: identify what the zeroed .data region in the modified iips.dll is.

Reconstructs the original structures at 0x10042000..0x10042400 from the
baseline copy and disassembles the .text stub at 0x10001000.
"""
import sys, struct, json
import pefile


STUB_VA_A = 0x10001000


def rva_to_off(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


def dump_struct(buf, rva, n):
    out = []
    for i in range(0, n, 4):
        if i + 4 <= len(buf):
            v = struct.unpack_from("<I", buf, i)[0]
            out.append({"rva": hex(rva + i), "u32": v, "hex": buf[i:i + 4].hex()})
    return out


def main():
    a_path = sys.argv[1]
    A = open(a_path, "rb").read()
    peA = pefile.PE(a_path, fast_load=True)
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    rep = {}
    # 1. the .text stub in baseline
    off = rva_to_off(peA, STUB_VA_A - peA.OPTIONAL_HEADER.ImageBase)
    rep["stub_orig_bytes"] = A[off:off + 24].hex()
    rep["stub_orig_va"] = hex(STUB_VA_A)

    # 2. what points at 0x10033d18 / 0x10033298 in the baseline
    for va in (0x10033d18, 0x10033298, 0x10001000):
        pat = struct.pack("<I", va)
        hits = []
        start = 0
        while True:
            i = A.find(pat, start)
            if i < 0:
                break
            r, s = None, None
            for sec in peA.sections:
                if sec.PointerToRawData <= i < sec.PointerToRawData + sec.SizeOfRawData:
                    r = i - sec.PointerToRawData + sec.VirtualAddress
                    s = sec.Name.rstrip(b"\x00").decode("latin1")
            hits.append({"off": hex(i), "rva": hex(r) if r else None,
                         "va": hex(peA.OPTIONAL_HEADER.ImageBase + r) if r else None,
                         "sec": s})
            start = i + 1
        rep["refs_%x" % va] = hits

    # 3. dump the zeroed region 0x10042000..0x10042400 from baseline
    off2 = rva_to_off(peA, 0x42000)
    rep["zeroed_region_rva_base"] = hex(0x10042000)
    rep["zeroed_region_orig"] = dump_struct(A, 0x10042000, 0x400)

    # 4. strings in that region
    blob = A[off2:off2 + 0x400]
    strs = []
    cur = b""
    start_i = 0
    for i, ch in enumerate(blob):
        if 0x20 <= ch < 0x7F:
            if not cur:
                start_i = i
            cur += bytes([ch])
        else:
            if len(cur) >= 4:
                strs.append({"off": hex(0x42000 + start_i), "s": cur.decode("latin1")})
            cur = b""
    rep["zeroed_region_strings"] = strs

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    if out_path:
        open(out_path, "w", encoding="utf-8").write(txt)
    print(json.dumps({k: v for k, v in rep.items() if k != "zeroed_region_orig"}, indent=1, ensure_ascii=False))
    print("zeroed_region_orig (first 64 dwords):")
    print(json.dumps(rep["zeroed_region_orig"][:64], indent=0, ensure_ascii=False))


if __name__ == "__main__":
    main()
