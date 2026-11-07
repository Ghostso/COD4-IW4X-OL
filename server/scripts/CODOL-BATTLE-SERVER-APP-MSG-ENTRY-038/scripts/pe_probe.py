import struct, json, sys
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read()
print('size',len(b))
e_lfanew=struct.unpack_from('<I',b,0x3c)[0]
print('e_lfanew',hex(e_lfanew),b[e_lfanew:e_lfanew+4])
coff=e_lfanew+4
machine,nsec,tstamp,ptrsym,nsym,optsize,chars=struct.unpack_from('<HHIIIHH',b,coff)
print('machine',hex(machine),'nsec',nsec,'tstamp',hex(tstamp),'optsize',hex(optsize),'chars',hex(chars))
opt=coff+20
magic=struct.unpack_from('<H',b,opt)[0]
print('magic',hex(magic))
imagebase=struct.unpack_from('<I',b,opt+28)[0] if magic==0x10b else struct.unpack_from('<Q',b,opt+24)[0]
sizeimage=struct.unpack_from('<I',b,opt+56)[0] if magic==0x10b else struct.unpack_from('<I',b,opt+56)[0]
entry=struct.unpack_from('<I',b,opt+16)[0]
print('imagebase',hex(imagebase),'sizeimage',hex(sizeimage),'entry',hex(entry))
sec=opt+optsize
rows=[]
for i in range(nsec):
 p=sec+i*40
 name=b[p:p+8].split(b'\0')[0].decode('latin1')
 vsize,vaddr,rawsize,rawptr,reloc,ln,ch=struct.unpack_from('<IIIIIIH',b,p+8)[0:7]
 rows.append((name,vaddr,vsize,rawptr,rawsize,rawptr+vsize,rawptr+rawsize,ch))
 print(f'{name:8s} VA={vaddr:#010x} VS={vsize:#010x} RAW={rawptr:#010x} RS={rawsize:#010x} endVA={vaddr+vsize:#010x} endRAW={rawptr+rawsize:#010x} ch={ch:#x}')
json.dump(rows,open(r'D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038\\evidence\\pe_sections.json','w'),indent=2)
