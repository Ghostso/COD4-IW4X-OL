import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

path = Path(r"COD OL\IIPS\iips.dll")
data = path.read_bytes()
md = Cs(CS_ARCH_X86, CS_MODE_32)

# map IAT slot VA to API name from pefile
import pefile
pe = pefile.PE(str(path))
pe.parse_data_directories()
iat_to_name = {}
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    dll = entry.dll.decode("latin1", "ignore")
    for imp in entry.imports:
        name = imp.name.decode("latin1", "ignore") if imp.name else "ord"
        iat_to_name[imp.address] = f"{dll}!{name}"

text_raw = 0x1000
text_va = 0x10000000 + 0x1000
text_size = 0x32000

blob = data[text_raw:text_raw+text_size]

call_events = []
for ins in md.disasm(blob, text_va):
    if ins.mnemonic == "call" and "[0x" in ins.op_str:
        # parse dword ptr [0xXXXXXXXX] / dword ptr [0xXXXXXXXX] ; comment
        import re
        m = re.search(r"0x([0-9a-fA-F]{8})", ins.op_str)
        if not m:
            continue
        iat_va = int(m.group(1), 16)
        api = iat_to_name.get(iat_va, hex(iat_va))
        # gather next instructions
        tail = []
        # disasm is streaming; we can decode from ins.address + ins.size manually
        off = ins.address + ins.size - text_va
        tail_blob = blob[off:off+64]
        for t in md.disasm(tail_blob, ins.address + ins.size):
            tail.append((t.address, t.mnemonic, t.op_str))
            if len(tail) >= 8:
                break
        call_events.append((ins.address, api, tail))

for va, api, tail in call_events:
    print("CALL", hex(va), api)
    for a, m, o in tail:
        mark = ""
        if m in ("test", "cmp"):
            mark = "<--"
        if m.startswith("j"):
            mark = "<--"
        print("  ", hex(a), m, o, mark)
