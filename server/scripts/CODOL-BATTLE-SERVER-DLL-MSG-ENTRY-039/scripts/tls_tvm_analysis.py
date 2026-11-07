import pefile,struct,capstone,math,collections,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
# Analyze .tls and .tvm0 sections: byte distributions, x86 prologue plausibility, E8 target plausibility
for name in ['.text','.tls','.tvm0']:
 s=[x for x in pe.sections if x.Name.rstrip(b'\0').decode()==name][0]
 data=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
 # entropy
 cnt=collections.Counter(data);ent=-sum((c/len(data))*math.log2(c/len(data)) for c in cnt.values())
 # common prologues
 pro=sum(1 for i in range(len(data)-4) if data[i]==0x55 and data[i+1]==0x8b and data[i+2]==0xec)
 int3=data.count(0xcc)
 e8=data.count(0xe8);e9=data.count(0xe9)
 print(f'{name}: VA={s.VirtualAddress:#x} raw={s.PointerToRawData:#x} size={len(data)} entropy={ent:.3f} prologue55_8b_ec={pro} cc={int3} e8={e8} e9={e9}')
 # first 64 bytes
 print('  first64',data[:64].hex())
# Test whether .tls bytes can be disassembled linearly with reasonable instruction flow
s=[x for x in pe.sections if x.Name.startswith(b'.tls')][0]
data=b[s.PointerToRawData:s.PointerToRawData+min(s.SizeOfRawData,0x2000)]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
valid=0;ins=list(md.disasm(data,IB+s.VirtualAddress))
valid=len(ins)
print('\n.tls first 0x2000 linear disasm instructions',valid,'bytes_covered',sum(i.size for i in ins))
for i in ins[:80]:print(f'{i.address-IB:08X} {i.bytes.hex():<18s} {i.mnemonic} {i.op_str}')
