import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n=160):
 return list(md.disasm(b[rva:rva+n],IB+rva))
for rva in [0x000A2E50,0x000A2650,0x000A2660,0x000A4CA0,0x000A4CAF,0x000A4A00,0x000A2250,0x001A07B0,0x001AC670,0x001AC650,0x001AC680]:
 print(f'\n===== RVA {rva:#x} =====')
 if rva<0 or rva>=len(b): print('OOB');continue
 print('bytes',b[rva:rva+16].hex())
 for i in dis(rva,120):print(fmt(i))
