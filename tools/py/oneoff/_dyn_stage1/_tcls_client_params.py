import pefile, capstone
from pathlib import Path
p=Path(r'COD OL\TCLS\Client.exe')
pe=pefile.PE(str(p), fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase
img=pe.get_memory_mapped_image()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
for start,end in [(0x401050,0x4012b0),(0x401250,0x401340)]:
    print('\n===',hex(start),hex(end),'===')
    for x in md.disasm(img[start-ib:end-ib],start):
        print(hex(x.address),x.bytes.hex(),x.mnemonic,x.op_str)
