import struct,capstone,json,re
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# Scan for prologues and build a boundary set in the executable range
entries=[]
for i in range(0x1000,min(len(b),0x8a6000)-3):
 if b[i]==0xcc and b[i+1]==0xcc and (b[i+2:i+6] in [b'\x55\x8b\xec\x83',b'\x55\x8b\xec\x81',b'\x55\x8b\xec\x53',b'\x55\x8b\xec\x56',b'\x55\x8b\xec\x57',b'\x55\x8b\xec\x6a',b'\x55\x8b\xec\x8b']):
  entries.append(i+2)
entries=sorted(set(entries))
print('prologue-boundary candidates (with two int3 prefix):',len(entries))
# Find jumps/calls to 0x5F830 and 0x1FF820 already done; now search functions that contain cmp/switch on 3/4/6 around 0x60000-0x70000
# Search byte patterns: cmp r/m32, imm8 03/04/06 and jcc nearby, then table jump
print('\n--- switch-like 03/04/06 comparison clusters ---')
for rva in range(0x10000,0x8a0000-16):
 # cmp eax/ecx/edx/ebx, imm8 patterns
 if b[rva] in (0x83,) and b[rva+1] in (0xf8,0xf9,0xfa,0xfb,0xfc,0xfd,0xfe,0xff) and b[rva+2] in (3,4,6):
  nxt=b[rva+3:rva+16]
  if b'\x0f\x84' in nxt or b'\x74' in nxt or b'\x75' in nxt or b'\xeb' in nxt:
   print(hex(rva),b[rva:rva+32].hex())
