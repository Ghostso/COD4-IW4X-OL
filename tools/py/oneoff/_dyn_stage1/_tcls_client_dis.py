import pefile, capstone, struct
from pathlib import Path
p=Path(r'COD OL\TCLS\Client.exe')
pe=pefile.PE(str(p), fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase
img=pe.get_memory_mapped_image()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail=True
code=img[0x1000:0x1e991]
base=ib+0x1000
ins=list(md.disasm(code,base))
byaddr={x.address:x for x in ins}
for target in (0x42228e,0x4222da):
    print('\n===',hex(target),'===')
    for x in ins:
        if target-96 <= x.address <= target+128:
            print(hex(x.address),x.mnemonic,x.op_str)
print('\nCALLS TO CREATE/SHELLEXEC')
targets={0x41f004:'CreateProcessW',0x41f13c:'ShellExecuteExW'}
for x in ins:
    if x.mnemonic in ('call','jmp'):
        for t,n in targets.items():
            if hex(t) in x.op_str:
                print(hex(x.address),x.mnemonic,x.op_str,n)
