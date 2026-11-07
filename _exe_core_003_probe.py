from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

p = Path(r"COD OL\codoMP_client_shipRetail.exe")
pe = pefile.PE(str(p))
ib = pe.OPTIONAL_HEADER.ImageBase
text = p.read_bytes()

for rva in [0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0]:
    sec = pe.get_section_by_rva(rva)
    name = sec.Name.rstrip(b"\x00").decode("latin1", "ignore") if sec else "UNKNOWN"
    raw = sec.PointerToRawData + (rva - sec.VirtualAddress) if sec else None
    print(f"RVA {hex(rva)} SEC {name} RAW {hex(raw) if raw is not None else 'NA'}")
    if raw is not None:
        blob = text[raw:raw + 64]
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        for i in md.disasm(blob, ib + rva):
            print(f"  {hex(i.address)} {i.mnemonic} {i.op_str}")
