import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
# enumerate callers of 0x1FF820 and 0x208380 exactly
for target in [0x1FF820,0x208380,0x5F830,0x5FF820,0x2000A0]:
 calls=[]
 for rva in range(0x1000,0x8a6000-5):
  if b[rva]==0xe8:
   rel=struct.unpack_from('<i',b,rva+1)[0]
   if (rva+5+rel)==target:calls.append(rva)
 print(f'callers of {target:#x}:',[hex(x) for x in calls])
# print wider caller windows
for label,rva,n in [('1FF820-entry',0x1FF820,900),('208380-entry',0x208380,700),('5F830-entry',0x5F830,300)]:
 print(f'\n===== {label} =====')
 for i in dis(rva,n): print(fmt(i))
