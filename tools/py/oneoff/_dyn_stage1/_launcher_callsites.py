from pathlib import Path
import pefile, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p = Path(r'COD OL/WeGameLauncher/launcher.exe')
data = p.read_bytes()
pe = pefile.PE(data=data, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
sites = [0x42ADB5, 0x448782, 0x44AADA, 0x44C120]
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
secs = [(base+s.VirtualAddress, base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData), s.Name.rstrip(b'\0').decode('latin1')) for s in pe.sections]
def sec_for(va):
    return next((n for a,b,n in secs if a <= va < b), '?')
def cstr(va, maxn=180):
    rva = va-base
    try: off = pe.get_offset_from_rva(rva)
    except Exception: return None
    if off < 0 or off >= len(data): return None
    end = data.find(b'\0', off, min(len(data), off+maxn))
    if end < 0: end = min(len(data), off+maxn)
    b = data[off:end]
    if not b: return ''
    printable = sum((32 <= x < 127) or x in (9,10,13) for x in b)/len(b)
    return b.decode('latin1') if printable > .85 else None
for site in sites:
    print('\n' + '='*100)
    print('CALL', hex(site), 'section', sec_for(site), 'fileoff', hex(pe.get_offset_from_rva(site-base)))
    lo, hi = site-0x180, site+0x50
    for ins in md.disasm(data[pe.get_offset_from_rva(lo-base):pe.get_offset_from_rva(hi-base)], lo):
        mark = '>>' if ins.address == site else '  '
        anno = ''
        if ins.mnemonic == 'push' and ins.operands and ins.operands[0].type == 3:
            s = cstr(ins.operands[0].imm)
            if s is not None: anno = ' ; STR ' + repr(s)
        print(f'{mark}{ins.address:08X} {ins.bytes.hex():<24} {ins.mnemonic:<8} {ins.op_str}{anno}')
