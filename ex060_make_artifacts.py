# EX-060: emit the evidence CSVs for the final report.
import csv
import os

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, callsite_info


def main():
    img = Image(DLL)
    imports = build_imports(img)
    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()
    fn = Function(img, 0x9860, "InitInGameApp").run().build_bbs()

    # --- ex060_callsites.csv
    with open("ex060_callsites.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["function", "rva", "insn", "kind", "target_dll",
                    "target_name", "target_rva", "evidence"])
        for fname, fnobj in (("CNIFS::initIfsLib", fi),
                             ("CNIFS::InitInGameApp", fn)):
            for rva, insn in fnobj.insns.items():
                if not insn.mnemonic.startswith("call"):
                    continue
                ci = callsite_info(fnobj, rva, insn, img, imports)
                lvl = "STATIC-DIRECT" if ci.get("kind") == "direct" else (
                    "STATIC-INDIRECT" if ci.get("kind") == "iat"
                    else "STATIC-INDIRECT")
                w.writerow([fname, "0x%X" % rva, ci["insn"], ci.get("kind"),
                            ci.get("dll", ""), ci.get("import", ""),
                            "0x%X" % ci["target_rva"] if "target_rva" in ci else "",
                            lvl])

    # --- ex060_globals.csv
    with open("ex060_globals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["function", "global_va", "site_rva", "instruction",
                    "access"])
        for fname, fnobj, lo, hi in (("CNIFS::initIfsLib", fi, 0x9570, 0x9860),
                                     ("CNIFS::InitInGameApp", fn, 0x9860, 0xA833)):
            for rva, insn in fnobj.insns.items():
                if not (lo <= rva <= hi):
                    continue
                for op in insn.operands:
                    if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                        acc = "READ" if insn.op_str.split(",")[0].strip() != \
                            "%s" % insn.op_str else "?"
                        w.writerow([fname, "0x%X" % op.mem.disp, "0x%X" % rva,
                                    "%s %s" % (insn.mnemonic, insn.op_str),
                                    "MEM"])

    print("wrote ex060_callsites.csv")
    print("wrote ex060_globals.csv")

    # --- ex060_8189fec_refs.csv (the full reference table; all negative)
    with open("ex060_8189fec_refs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "module_base", "module_size", "encoding",
                    "raw_offset", "rva", "va", "kind"])
        mods = [
            ("codoMP_client_shipRetail.exe", os.path.join(
                "工具", "EX035_DIR", "codoMP_client_shipRetail.exe")),
            ("codoMP_client_shipRetailBase.dll", os.path.join(
                "工具", "EX035_DIR", "codoMP_client_shipRetailBase.dll")),
            ("iips.dll", os.path.join("工具", "EX035_DIR", "IIPS", "iips.dll")),
            ("IIPSHost.dll", os.path.join(
                "工具", "EX035_DIR", "IIPS", "IIPSHost.dll")),
            ("IIPSVFS.dll", os.path.join(
                "工具", "EX035_DIR", "IIPS", "IIPSVFS.dll")),
            ("IIPSHostApp.exe", os.path.join(
                "工具", "EX035_DIR", "IIPS", "IIPSHostApp.exe")),
            ("TenProxy.dll", os.path.join("工具", "EX035_DIR", "TenProxy.dll")),
            ("GbSpy.dll", os.path.join("工具", "EX035_DIR", "GbSpy.dll")),
            ("BugTrace.dll", os.path.join("工具", "EX035_DIR", "BugTrace.dll")),
        ]
        import pefile
        import struct
        for label, p in mods:
            if not os.path.exists(p):
                continue
            pe = pefile.PE(p, fast_load=True)
            base = pe.OPTIONAL_HEADER.ImageBase
            size = pe.OPTIONAL_HEADER.SizeOfImage
            data = open(p, "rb").read()
            found = False
            for enc, needle in (("le32", struct.pack("<I", 0x8189FEC)),
                                ("be32", struct.pack(">I", 0x8189FEC)),
                                ("ascii", b"8189FEC")):
                st = 0
                while True:
                    i = data.find(needle, st)
                    if i < 0:
                        break
                    found = True
                    w.writerow([label, "0x%X" % base, "0x%X" % size, enc,
                                "0x%X" % i, "", "", "UNRESOLVED"])
                    st = i + 1
            if not found:
                w.writerow([label, "0x%X" % base, "0x%X" % size, "none",
                            "", "", "", "NO_REFERENCE"])
    print("wrote ex060_8189fec_refs.csv")


if __name__ == "__main__":
    main()
