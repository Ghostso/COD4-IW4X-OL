# -*- coding: utf-8 -*-
"""S2-H: disassemble around the enable_iips / iips_url / IIPS error strings
in codoMP_client_shipRetail.exe and find the enclosing function + refs.

Static only.
"""
import sys, json, struct
import pefile
import capstone


TARGETS = {
    "iips_debug": 0x00DDBE38,
    "iips.ini": 0x00DDBE44,
    "enable_iips=%d": 0x00DDBE50,
    "iips_url=%s": 0x00DDBE60,
    "iips.dll": 0x00DC93F5,
    "WIN_IIPS_INIT_ERROR": 0x00DC93A8,
    "WIN_IIPS_PREDOWNLOAD_ERROR": 0x00DC93BC,
    "WIN_IIPS_INIT_FAILED": 0x00DC93D8,
    "WIN_IIPS_DLL_ERROR": 0x00DC9408,
    "0x%x": 0x00DC9400,
    "iips_enableOptionalDownloads": 0x00DDBE78,
}


def va_to_off(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress), s.Name.rstrip(b"\x00").decode("latin1")
    return None, None


def main():
    path = sys.argv[1]
    pe = pefile.PE(path, fast_load=True)
    raw = open(path, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase

    rep = {"file": path, "imagebase": hex(base)}

    # locate the .tp3 with raw backing that contains our strings
    for name, va in TARGETS.items():
        off, sec = va_to_off(pe, va)
        if off is None:
            rep[name] = {"va": hex(va), "error": "va not mapped"}
            continue
        pat = struct.pack("<I", va)
        hits = []
        start = 0
        while True:
            i = raw.find(pat, start)
            if i < 0:
                break
            # compute va of the hit
            rva = None
            secname = None
            for s in pe.sections:
                if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
                    rva = i - s.PointerToRawData + s.VirtualAddress
                    secname = s.Name.rstrip(b"\x00").decode("latin1")
                    break
            hits.append({"off": hex(i), "va": hex(base + rva) if rva else None, "sec": secname})
            start = i + 1
        rep[name] = {"va": hex(va), "sec": sec, "file_off": hex(off),
                     "body": raw[off:off + 40].split(b"\x00")[0].decode("latin1", "replace"),
                     "ptr_refs": hits}

    json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False)[:12000])


if __name__ == "__main__":
    main()
