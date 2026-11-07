# -*- coding: utf-8 -*-
"""S2-F: characterize .tp3 section of codoMP_client_shipRetail.exe."""
import sys, json, struct
import pefile


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    pe = pefile.PE(path, fast_load=True)
    rep = {"file": path, "imagebase": hex(pe.OPTIONAL_HEADER.ImageBase),
           "ep": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), "sections": []}
    for s in pe.sections:
        rep["sections"].append({
            "name": s.Name.rstrip(b"\x00").decode("latin1"),
            "va": hex(s.VirtualAddress),
            "vsize": hex(s.Misc_VirtualSize),
            "raw": hex(s.PointerToRawData),
            "rawsize": hex(s.SizeOfRawData),
            "chars": hex(s.Characteristics),
            "file_end": s.PointerToRawData + s.SizeOfRawData,
        })

    # Which section does 0xDC93A8 (WIN_IIPS_INIT_ERROR) resolve to?
    va = 0x00DC93A8
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    off = None
    sec_name = None
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            sec_name = s.Name.rstrip(b"\x00").decode("latin1")
            off = s.PointerToRawData + (rva - s.VirtualAddress)
            break
    rep["iips_err_string"] = {"va": hex(va), "rva": hex(rva), "sec": sec_name,
                              "file_off": hex(off) if off is not None else None,
                              "in_raw": bool(off is not None and off + 32 <= len(open(path, "rb").read()))}
    if off is not None and off + 64 <= len(open(path, "rb").read()):
        raw = open(path, "rb").read()
        rep["bytes_at_off"] = raw[off:off + 64].hex()

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
