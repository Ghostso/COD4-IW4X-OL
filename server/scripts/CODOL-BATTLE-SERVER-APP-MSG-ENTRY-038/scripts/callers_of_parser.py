import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
# print windows around caller clusters
for label,rva,n in [('6D360 callers',0x156f80,0x500),('6DA30 callers',0x150580,0x600),('6D060 caller',0x6d580,0x180),('6DCF0 callers',0x6df00,0x200),('6E030 caller',0x6e900,0x180),('6E0A0 caller',0x6e480,0x180)]:
 print(f'\n########## {label} @ {rva:#x} ##########')
 for i in dis(rva,n):print(fmt(i))
