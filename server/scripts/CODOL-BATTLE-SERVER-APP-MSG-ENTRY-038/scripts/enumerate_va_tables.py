import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<24s} {i.mnemonic} {i.op_str}".rstrip()
def dis(rva,n):return list(md.disasm(b[rva:rva+n],IB+rva))
# Find all functions that contain an indirect jump whose disp32 is VA (>=IB) and table has valid text targets
tables=[]
for i in range(0x1000,min(len(b),0x8a6000)-7):
 if b[i:i+2]!=b'\xff\x24':continue
 ins=list(md.disasm(b[i:i+7],IB+i))
 if not ins:continue
 x=ins[0]
 if x.mnemonic!='jmp' or 'dword ptr' not in x.op_str or '*4' not in x.op_str:continue
 # get disp32 as bytes after modrm (ff 24 modrm disp32)
 if len(x.bytes)<7:continue
 disp=struct.unpack_from('<I',b,i+3)[0]
 if disp<IB:continue
 tab=disp-IB
 if tab+4*32>len(b):continue
 vals=[struct.unpack_from('<I',b,tab+j*4)[0] for j in range(32)]
 valid=[v-IB for v in vals if IB+0x1000<=v<IB+0x8a6000]
 if len(valid)>=4:
  tables.append((i,tab,len(valid),valid[:8],x.op_str))
print('valid VA-based indirect tables:',len(tables))
for t in tables[:160]:print(hex(t[0]),hex(t[1]),t[2],[hex(x) for x in t[3]],t[4])
json.dump(tables,open(r'D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038\\evidence\\va_indirect_tables.json','w'),indent=2)
