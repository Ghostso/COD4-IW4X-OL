import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
for rva,n,label in [(0x5FF820,1600,'5FF820 full'),(0x2000A0,1800,'2000A0 full'),(0x200F00,400,'caller 200F00')]:
 print(f'\n########## {label} ##########')
 for i in dis(rva,n): print(fmt(i))
