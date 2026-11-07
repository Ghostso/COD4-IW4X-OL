from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM
p = Path(r'COD OL/TCLS/Client.exe')
d = p.read_bytes()
pe = pefile.PE(data=d, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def va_to_off(va):
    return pe.get_offset_from_rva(va - base)

def read_cstr(va, n=512):
    try: o = va_to_off(va)
    except Exception: return None
    if o is None or o < 0 or o >= len(d): return None
    e = d.find(b'\0', o, min(len(d), o+n))
    if e < 0: e = min(len(d), o+n)
    b = d[o:e]
    if len(b) < 2: return None
    try:
        s = b.decode('utf-8')
    except Exception:
        return None
    if any(ord(c) < 32 and c not in '\t\r\n' for c in s): return None
    return s

def read_wstr(va, n=512):
    try: o = va_to_off(va)
    except Exception: return None
    if o is None or o < 0 or o >= len(d): return None
    e = o
    while e + 1 < len(d) and e < o+n and d[e:e+2] != b'\0\0': e += 2
    if e == o: return None
    try: s = d[o:e].decode('utf-16le')
    except Exception: return None
    if any(ord(c) < 32 and c not in '\t\r\n' for c in s): return None
    return s

# all direct refs into target range from .text
text = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.text')
tv = base + text.VirtualAddress
print('ENTRY', hex(base + pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print('DIRECT REFS INTO 0x401000..0x401e80')
for ins in md.disasm(text.get_data(), tv):
    if ins.mnemonic in ('call','jmp') and ins.operands and ins.operands[0].type == CS_OP_IMM:
        t = ins.operands[0].imm
        if 0x401000 <= t < 0x401e80:
            print(f'{ins.address:08X} {ins.mnemonic} {hex(t)}')

print('\nDISASM 0x401000..0x401b00')
start, end = 0x401000, 0x401b00
o1, o2 = va_to_off(start), va_to_off(end)
for ins in md.disasm(d[o1:o2], start):
    ann = ''
    if ins.operands and ins.operands[0].type == CS_OP_IMM:
        x = ins.operands[0].imm & 0xffffffff
        c = read_cstr(x)
        w = read_wstr(x)
        if c is not None: ann = ' ; ASCII=' + repr(c)
        elif w is not None: ann = ' ; UTF16=' + repr(w)
    print(f'{ins.address:08X}: {ins.bytes.hex():<20} {ins.mnemonic:<8} {ins.op_str}{ann}')
