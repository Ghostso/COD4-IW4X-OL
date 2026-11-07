from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

p = Path(r"COD OL\codoMP_client_shipRetail.exe")
pe = pefile.PE(str(p))
ib = pe.OPTIONAL_HEADER.ImageBase
text = p.read_bytes()

ranges = [
    (0x77F540, 0x77F620),
    (0x77F8A0, 0x77F920),
    (0x4FD980, 0x4FDA60),
    (0x4FCEB0, 0x4FCF70),
    (0x808620, 0x8086C0),
    (0x7E98C0, 0x7E9980),
    (0x621280, 0x621340),
]
for start, end in ranges:
    sec = pe.get_section_by_rva(start)
    name = sec.Name.rstrip(b"\x00").decode("latin1", "ignore") if sec else "UNKNOWN"
    raw = sec.PointerToRawData + (start - sec.VirtualAddress) if sec else None
    print(f"=== RVA {hex(start)} SEC {name} RAW {hex(raw) if raw is not None else 'NA'} ===")
    if raw is None:
        continue
    blob = text[raw:raw + (end - start)]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in md.disasm(blob, ib + start):
        print(f"{hex(i.address)} {i.mnemonic} {i.op_str}")
