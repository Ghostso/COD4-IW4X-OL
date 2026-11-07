import struct,pefile,sys
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); d=open(P,'rb').read()
for s in pe.sections:
 print(s.Name.rstrip(b'\0'),hex(s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.PointerToRawData),hex(s.SizeOfRawData),hex(s.Characteristics))
# parse .rimp raw
sec=[s for s in pe.sections if s.Name.startswith(b'.rimp')][0]
raw=d[sec.PointerToRawData:sec.PointerToRawData+sec.SizeOfRawData]
print('RIMP RAW',raw[:256].hex())
# try records: (target_va, delta) or similar; scan 4-byte pairs
for stride in (8,12,16):
 print('STRIDE',stride)
 for i in range(0,min(len(raw)-stride,stride*12),stride):
  vals=struct.unpack_from('<'+'I'*(stride//4),raw,i)
  print(i,[hex(x) for x in vals])
