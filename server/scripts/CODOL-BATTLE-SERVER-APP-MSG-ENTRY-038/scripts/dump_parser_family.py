import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
for rva in [0x6D060,0x6D360,0x6D6E0,0x6D870,0x6D960,0x6D9D0,0x6DA30,0x6DAE0,0x6DCF0,0x6E030,0x6E0A0]:
 print(f'\n===== parser family {rva:#x} =====')
 for i in dis(rva,260):print(fmt(i))
