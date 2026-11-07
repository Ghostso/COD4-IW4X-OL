"""Read-only C1 PE inspection for the ACTION_SLOT_HELP binding token."""
import argparse
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def main(path):
    pe = pefile.PE(path, fast_load=True)
    data = open(path, "rb").read()
    image = pe.OPTIONAL_HEADER.ImageBase
    token = b"ACTION_SLOT_HELP\0"
    token_offsets = []
    start = 0
    while (at := data.find(token, start)) >= 0:
        token_offsets.append(at)
        start = at + 1
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    for file_offset in token_offsets:
        rva = pe.get_rva_from_offset(file_offset)
        va = image + rva
        print(f"token file={file_offset:#x} va={va:#x}")
        refs = []
        packed = struct.pack("<I", va)
        for section in pe.sections:
            if not section.Name.startswith(b".text"):
                continue
            code = section.get_data()
            at = 0
            while (pos := code.find(packed, at)) >= 0:
                ref_va = image + section.VirtualAddress + pos
                refs.append(ref_va)
                at = pos + 1
        for ref_va in refs:
            print(f"  candidate immediate {ref_va:#x}")
            rva = ref_va - image
            surrounding = pe.get_data(rva - 89, 290)
            for ins in decoder.disasm(surrounding, ref_va - 89):
                if ref_va - 89 <= ins.address <= ref_va + 195:
                    print(f"    {ins.address:#x} {ins.mnemonic} {ins.op_str}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    main(parser.parse_args().path)
