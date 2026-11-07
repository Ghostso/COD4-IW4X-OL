from pathlib import Path
import pefile,re,struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
path=r'COD OL\WeGameLauncher\launcher.exe'
pe=pefile.PE(path,fast_load=True); data=Path(path).read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# dump region containing the branch, from a likely function start to before next aligned prologue
text=pe.sections[0]; blob=text.get_data(); tva=base+text.VirtualAddress
starts=[]
for off in range(0,len(blob)-3):
    if blob[off:off+3] in (b'\x55\x8b\xec', b'\x6a\xff\x68', b'\x53\x56\x57'):
        starts.append(tva+off)
for lo,hi in [(0x412450,0x412c20),(0x412f00,0x413430),(0x411d00,0x412c20)]:
    print('\n'+'='*110); print('REGION',hex(lo),hex(hi))
    o=lo-base; e=hi-base
    for ins in md.disasm(blob[o:e],lo):
        print(f'{ins.address-base:08X} {ins.bytes.hex():<24} {ins.mnemonic} {ins.op_str}')
# extract exact names (ascii) that look like Windows object or path/config names, and wide variants
print('\n'+'='*110); print('OBJECT/PATH STRINGS')
pat=re.compile(rb'[\x20-\x7e]{5,200}')
for m in pat.finditer(data):
    s=m.group().decode('latin1')
    low=s.lower()
    if (('mutex' in low or 'event' in low or 'mapping' in low or 'pipe' in low or 'shared' in low or 'instance' in low or 'zombie' in low or 'tcls' in low or 'wegame' in low or 'launcher' in low) and not ('xmp' in low or 'definition' in low or 'instanceid' in low)):
        if 'http' in low or 'adobe' in low: continue
        try:va=base+pe.get_rva_from_offset(m.start())
        except:continue
        print(f'{va:08X} {s!r}')
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){5,200}',data):
    s=m.group().decode('utf-16le','ignore')
    low=s.lower()
    if (('mutex' in low or 'event' in low or 'mapping' in low or 'pipe' in low or 'shared' in low or 'instance' in low or 'zombie' in low or 'tcls' in low or 'wegame' in low or 'launcher' in low) and not ('xmp' in low or 'definition' in low or 'instanceid' in low)):
        if 'http' in low or 'adobe' in low: continue
        try:va=base+pe.get_rva_from_offset(m.start())
        except:continue
        print(f'{va:08X} W {s!r}')
