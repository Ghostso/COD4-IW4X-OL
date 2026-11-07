import os
import struct

import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio"
ORIG = r"COD OL\IIPS\Tenio"

# From GetComponentIDs disassembly: (global_count_address, global_table_address)
TABLES = {
    "June.dll": (0x100CC0F0, 0x100CC0F4),
    "TenFact.dll": (0x1001A6F0, 0x1001A6F4),
    "MemoryAlloctor.dll": (0x1000A468, 0x1000A46C),
    "ScriptManager.dll": (0x10091990, 0x10091994),
}


def read_dword_at(pe, data, va):
    image_base = pe.OPTIONAL_HEADER.ImageBase
    rva = va - image_base
    try:
        off = pe.get_offset_from_rva(rva)
    except Exception:
        return None
    if off is None or off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, off)[0]


def main():
    for root_label, root in (("SANDBOX", IIPS), ("ORIGINAL", ORIG)):
        print("=" * 90)
        print(root_label, root)
        for name, (count_va, table_va) in TABLES.items():
            path = os.path.join(root, name)
            if not os.path.exists(path):
                print(f"  {name}: missing")
                continue
            data = open(path, "rb").read()
            pe = pefile.PE(path, fast_load=True)
            count = read_dword_at(pe, data, count_va)
            print(f"  {name}: declared_count={count} count_va=0x{count_va:X}")
            if count is None or count <= 0 or count > 512:
                print("     (table not statically initialized or count invalid)")
                continue
            ids = []
            for i in range(count):
                entry_va = table_va + i * 8
                value = read_dword_at(pe, data, entry_va)
                ids.append(value)
            print("     ids:", ids)
            print("     has985:", 985 in ids)


if __name__ == "__main__":
    main()
