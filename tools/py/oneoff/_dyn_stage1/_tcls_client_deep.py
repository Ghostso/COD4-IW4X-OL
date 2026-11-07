import pefile, capstone, struct
from pathlib import Path
p=Path(r'COD OL\TCLS\Client.exe')
pe=pefile.PE(str(p),fast_load=False); ib=pe.OPTIONAL_HEADER.ImageBase; img=pe.get_memory_mapped_image()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
for start,end in [(0x4012ac,0x401500),(0x401500,0x401800)]:
 print('\n===',hex(start),hex(end),'===')
 for x in md.disasm(img[start-ib:end-ib],start): print(hex(x.address),x.bytes.hex(),x.mnemonic,x.op_str)
print('\n=== RDATA 0x41f400-0x41f700 ===')
b=img[0x1f400:0x1f700]
for off in range(0,len(b),16):
 chunk=b[off:off+16]
 txt=''.join(chr(c) if 32<=c<127 else '.' for c in chunk)
 print(hex(ib+0x1f400+off),chunk.hex(' '),txt)
