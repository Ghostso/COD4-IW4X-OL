import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
for rva,n in [(0x20057C,0x40),(0x5F830,0x120),(0x5FF820,0x120),(0x208380,0x100)]:
 print(f'=== {rva:#x} ===')
 for i in md.disasm(b[rva:rva+n],IB+rva): print(f'{i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}')
print('\n=== actual dispatch targets at 0x600744 (as addresses) ===')
for idx in range(26):
 t=struct.unpack_from('<I',b,0x600744+idx*4)[0]
 idxb=b[0x60077c+idx]
 print(f'idx {idx:2d} raw={t:#010x} byte={idxb:#04x} target={t:#010x} byte@target={b[t:t+8].hex() if 0<=t<len(b) else "OOB"}')
