import pefile, capstone, sys
from pathlib import Path
p=Path(r'COD OL\TCLS\Client.exe')
pe=pefile.PE(str(p), fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase; img=pe.get_memory_mapped_image()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
print('=== function 0x401000 head ===')
for x in md.disasm(img[0x1000:0x1070],0x401000): print(hex(x.address),x.bytes.hex(),x.mnemonic,x.op_str)
print('\n=== callers/jumps to 0x401000 ===')
for x in md.disasm(img[0x1000:0x1e991],0x401000):
    if x.mnemonic in ('call','jmp') and ('0x401000' in x.op_str): print(hex(x.address),x.mnemonic,x.op_str)
print('\n=== strings ===')
for va in [0x41f418,0x41f450,0x41f47c,0x41f488,0x41f4c0,0x41f4f8,0x41f550]:
    off=va-ib
    b=img[off:off+512]
    z=min([i for i in [b.find(b'\0'),b.find(b'\0\0')] if i>=0]+[512])
    u=b[:z].decode('utf-16le','backslashreplace')
    a=b[:min(z,256)].decode('latin1','backslashreplace')
    print(hex(va),'utf16=',ascii(u),' raw=',ascii(a))
