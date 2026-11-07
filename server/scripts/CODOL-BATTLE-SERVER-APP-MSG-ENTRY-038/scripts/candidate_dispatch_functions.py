import struct,capstone
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
def callers(t):
 out=[]
 for i in range(0x1000,min(len(b),0x8a6000)-5):
  if b[i]==0xe8:
   rel=struct.unpack_from('<i',b,i+1)[0]
   if i+5+rel==t:out.append(i)
 return out
for name,rva in [('0x5d92b',0x5d92b),('0x39634',0x39634),('0x6728c',0x6728c),('0x73bb8',0x73bb8)]:
 print(f'\n########## candidate {name} ##########')
 print('callers',[hex(x) for x in callers(rva)])
 # find function entry by scanning back to int3 boundary
 s=rva
 while s>0x1000 and not (b[s-1]==0xcc and b[s-2]==0xcc):s-=1
 print('nearest CC boundary',hex(s),b[s:s+12].hex())
 for i in dis(s,700):print(fmt(i))
