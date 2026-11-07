import struct, capstone, json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read()
IB=0x400000
# for low RVAs in first raw section RVA==file offset
def off(rva): return rva
def dis(rva,n=80,show=True):
    code=b[off(rva):off(rva)+n]
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    md.detail=True
    ins=list(md.disasm(code,IB+rva))
    lines=[]
    for i in ins:
        s=f"{i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}".rstrip()
        lines.append(s)
        if show: print(s)
    return lines
print('=== around 0x20059B ===')
dis(0x200560,80)
print('\n=== find prologue before 0x20059B ===')
p=b.rfind(b'\x55\x8b\xec',0x1F0000,0x20059C)
print('last push ebp/mov ebp,esp before site:',hex(p) if p>=0 else None)
p2=max([b.rfind(pat,0x1F0000,0x20059C) for pat in [b'\x55\x8b\xec',b'\x6a\xff\x68',b'\x8b\xff\x55\x8b\xec']])
print('best',hex(p2))
# dump int3 boundaries around 0x20059B
start=max(0,0x1FF000); end=0x201000
runs=[];i=start
while i<end:
 if b[i]==0xcc:
  j=i
  while j<end and b[j]==0xcc:j+=1
  if j-i>=4:runs.append((i,j,j-i))
  i=j
 else:i+=1
print('int3 runs >=4 around site:')
for r in runs:
 if abs(r[0]-0x20059B)<0x120: print(hex(r[0]),hex(r[1]),r[2])
