import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
def u32(r):return struct.unpack_from('<I',b,r)[0]
def s32(r):return struct.unpack_from('<i',b,r)[0]
def dis(rva,n=200):
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
 return list(md.disasm(b[rva:rva+n],IB+rva))
def fmt(ins):return f"{ins.address-IB:08X} {ins.bytes.hex():<20s} {ins.mnemonic} {ins.op_str}".rstrip()
print('=== bytes/tables ===')
print('table 0x600744 first 32 dwords')
raw=b[0x600744:0x600744+32*4]
for i in range(26):
 t=struct.unpack_from('<I',raw,i*4)[0]
 print(f'  idx {i:2d}: table={t:#010x}')
print('index bytes 0x60077c first 26:',' '.join(f'{x:02x}' for x in b[0x60077c:0x60077c+26]))
print('\n=== dispatch prologue from 0x2000A0 ===')
for i in dis(0x2000A0,220):print(fmt(i))
