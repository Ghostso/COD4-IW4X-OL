# Targeted cross-references for the IIPS pipe command handlers and the
# TPFUI path-construction bug.
#
# Scans executable sections for direct rel32 calls/jumps to target VAs,
# and finds ASCII strings around TPFUI / IIPSRes / loader errors.
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import re

TARGETS = {
    r"COD OL\IIPS\iips.dll": [
        0x100153B0,  # cmd=1/cmd=2 reply builder (SetHostAction?)
        0x10016DD0,  # cmd=2 handler calls this (OnSyncReturn)
        0x10016AC0,
        0x10017920,
    ],
    r"COD OL\IIPS\IIPSHost.dll": [
        # filled after string scan if needed
    ],
}


def sections(pe):
    for sec in pe.sections:
        name = sec.Name.rstrip(b"\0").decode("latin1")
        if sec.Characteristics & 0x20000000:
            yield name, sec


def main():
    for path, targets in TARGETS.items():
        pe = pefile.PE(path)
        base = pe.OPTIONAL_HEADER.ImageBase
        blob = open(path, "rb").read()
        print("===== %s base=0x%08X =====" % (path, base))

        md = Cs(CS_ARCH_X86, CS_MODE_32)
        for sec_name, sec in sections(pe):
            raw = blob[sec.PointerToRawData:
                       sec.PointerToRawData + sec.SizeOfRawData]
            va = base + sec.VirtualAddress
            for ins in md.disasm(raw, va):
                if ins.mnemonic not in ("call", "jmp"):
                    continue
                try:
                    dest = int(ins.op_str, 16)
                except ValueError:
                    continue
                if dest in targets:
                    print("  %s xref 0x%08X -> 0x%08X" % (
                        sec_name, ins.address, dest))
        print()

        print("=== TPFUI / IIPSRes strings ===")
        for m in re.finditer(rb"[\x20-\x7e]{3,}", blob):
            text = m.group().decode("latin1")
            if any(k in text for k in (
                    "TPFUI", "IIPSRes", "LoadImage", "TPFFile",
                    "TPFUI.tprj", "Style", "Layout", "IIPS\\",
                    "Can't find Component")):
                print("  +0x%06X VA 0x%08X  %r" % (
                    m.start(), base + m.start(), text[:240]))
        print()


main()
