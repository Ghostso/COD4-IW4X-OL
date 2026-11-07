import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def dis(rva,n=200):
 return list(md.disasm(b[rva:rva+n],IB+rva))
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
# candidate VAs from Atlas -> RVAs
cands=[('0xA2E50',0xA2E50),('0xA2660',0xA2660),('0xA4CAF',0xA4CAF),('0x49F2E5',0x49F2E5),('0x4A1A65',0x4A1A65),('0x3512A0',0x3512A0),('0x352E80',0x352E80),('0x1A07B0',0x1A07B0),('0x1AC670',0x1AC670)]
print('===== VA -> RVA candidates =====')
for name,va in cands:
 rva=va-IB
 print(f'{name}: rva={rva:#x} bytes={b[rva:rva+12].hex() if 0<=rva<len(b) else "OOB"}')
 print('  first insns:',[fmt(i) for i in dis(rva,48)][:8])
# Scan for likely bitstream reader functions around 0x1A0000-0x1B0000
print('\n===== candidates containing bit-reader patterns =====')
patterns=[b'\x83\xe9\x08',b'\xc1\xe8',b'\x0f\xb6',b'\x8b\x45\x0c',b'\x8b\x4d\x10']
# Search immediate-compare dispatch patterns in low code range
print('cmp reg,0x03 followed by cmp/jcc patterns in 0x5F000-0x70000:')
for rva in range(0x5F000,0x70000):
 if b[rva:rva+2]==b'\x83\xf8\x03' or b[rva:rva+2]==b'\x83\xf9\x03' or b[rva:rva+2]==b'\x83\xfa\x03' or b[rva:rva+2]==b'\x83\xfb\x03':
  print(' ',hex(rva),b[rva:rva+24].hex())
