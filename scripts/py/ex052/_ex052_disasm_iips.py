from pathlib import Path
import re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

path = Path(r'COD OL\IIPS\iips.dll')
data = path.read_bytes()
pe = pefile.PE(str(path))
pe.parse_data_directories()
base = pe.OPTIONAL_HEADER.ImageBase


def va(off):
    return base + off


def text_blob():
    return data[0x1000:0x1000 + pe.sections[0].Misc_VirtualSize]


def disasm(start, limit=220):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    blob = text_blob()
    print(f'=== start RVA {hex(start)} VA {hex(va(start))} ===')
    count = 0
    for i in md.disasm(blob[start - 0x1000:], va(start)):
        ops = i.op_str
        mark = ''
        if i.mnemonic in ('test', 'cmp') or i.mnemonic.startswith('j'):
            mark = ' <--'
        print(f"{hex(i.address)} {i.mnemonic} {ops}{mark}")
        count += 1
        if count >= limit:
            break


def refs(pattern_bytes):
    rdata = data[0x33000:0x33000 + 0xEC81]
    print('RData refs for', pattern_bytes)
    for m in re.finditer(re.escape(pattern_bytes), rdata):
        print(' ', hex(0x33000 + m.start()))


for rva in [0x9550, 0x9570, 0x9860, 0x9870, 0x9A00, 0x9B50, 0x15A00, 0x15CD0]:
    disasm(rva)

refs(b'IFS2.dll')
refs(b'ifs2.dll')
refs(b'IIPSHostApp.ini')
refs(b'IIPSHostApp.exe')
refs(b'ReservedSize')
refs(b'[ResPool]')

print('\nImports:')
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    dll = entry.dll.decode('latin1', 'ignore')
    for imp in entry.imports:
        print(dll, hex(imp.address), imp.name.decode('latin1', 'ignore') if imp.name else 'ord')
