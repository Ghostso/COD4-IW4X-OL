# -*- coding: utf-8 -*-
"""S2-J: prove what the 0x12345678 stub + zeroed .data does.

Compares the modified iips.dll against the baseline in the two places that
matter for DLL loading:
  - DllMain / entrypoint region (0x10001000)
  - TLS callback table + .data init structures
and reports whether the zeroed .data region is referenced by the code.
"""
import sys, json, struct
import pefile
import capstone


BASE_A = r"工具\EX035_DIR\IIPS\iips.dll"
BASE_B = r"COD OL\IIPS\iips.dll"


def va_to_off(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress), s.Name.rstrip(b"\x00").decode()
    return None, None


def main():
    peA = pefile.PE(BASE_A, fast_load=True)
    peA.parse_data_directories()
    A = open(BASE_A, "rb").read()
    B = open(BASE_B, "rb").read()

    rep = {}
    # Entry point
    ep_rva = peA.OPTIONAL_HEADER.AddressOfEntryPoint
    ep_va = peA.OPTIONAL_HEADER.ImageBase + ep_rva
    off, sec = va_to_off(peA, ep_va)
    rep["entry"] = {"va": hex(ep_va), "sec": sec, "off": hex(off),
                    "A": A[off:off + 32].hex(), "B": B[off:off + 32].hex(),
                    "identical": A[off:off + 32] == B[off:off + 32]}

    # TLS callbacks
    if hasattr(peA, "DIRECTORY_ENTRY_TLS"):
        tls = peA.DIRECTORY_ENTRY_TLS.struct
        rep["tls"] = {"start_raw": hex(tls.StartAddressOfRawData),
                      "end_raw": hex(tls.EndAddressOfRawData),
                      "address_index": hex(tls.AddressOfIndex),
                      "callbacks": hex(tls.AddressOfCallBacks)}
        cb_va = tls.AddressOfCallBacks
        o, s = va_to_off(peA, cb_va)
        if o is not None:
            cbs = []
            i = 0
            while True:
                v = struct.unpack_from("<I", A, o + i * 4)[0]
                if v == 0:
                    break
                cbs.append(hex(v))
                i += 1
                if i > 16:
                    break
            rep["tls"]["callback_list"] = cbs
            rep["tls"]["callback_list_B"] = []
            for cb in cbs:
                o2, s2 = va_to_off(peA, int(cb, 16))
                if o2 is not None:
                    rep["tls"]["callback_list_B"].append(
                        {"cb": cb, "A": A[o2:o2 + 16].hex(), "B": B[o2:o2 + 16].hex(),
                         "same": A[o2:o2 + 16] == B[o2:o2 + 16]})

    # does the stub appear in the export name table?
    rep["file_offset_0x1000_note"] = (
        "0x1000 is the first byte of .text (RVA 0x1000). "
        "Baseline: 'mov dword ptr [ecx], 0x10033d18; jmp [0x10033298]' "
        "(a vtable/ctor thunk). Modified: 'mov eax,0x12345678; ret; ret' (debug stub)."
    )

    # .data head around 0x10042000
    o3, s3 = va_to_off(peA, 0x10042000)
    rep["data_0x10042000"] = {"off": hex(o3), "sec": s3,
                              "A": A[o3:o3 + 0x40].hex(), "B": B[o3:o3 + 0x40].hex()}

    # 0x4d5a9000 => 'MZ\x90\x00' -> an embedded MZ header (nested PE or resource blob)
    rep["embedded_MZ_at_10042000"] = A[o3:o3 + 2] == b"MZ"
    if A[o3:o3 + 2] == b"MZ":
        lfanew = struct.unpack_from("<I", A, o3 + 0x3C)[0]
        rep["embedded_MZ_lfanew"] = hex(lfanew)
        if 0 < lfanew < 0x200:
            sig = A[o3 + lfanew:o3 + lfanew + 4]
            rep["embedded_MZ_sig"] = sig.hex()
            rep["embedded_MZ_valid_PE"] = sig == b"PE\x00\x00"

    # 0x1003bfb4 ref to 0x10001000 from .rdata
    o4, s4 = va_to_off(peA, 0x1003BFB4)
    rep["rdata_ref_10001000"] = {"off": hex(o4), "sec": s4,
                                 "A": A[o4 - 16:o4 + 48].hex(),
                                 "B": B[o4 - 16:o4 + 48].hex()}

    json.dump(rep, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
