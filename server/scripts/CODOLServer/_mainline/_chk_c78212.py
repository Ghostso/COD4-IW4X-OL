import struct
exe = r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
data=open(exe,'rb').read()
pe=struct.unpack_from('<I',data,0x3C)[0]
nsec=struct.unpack_from('<H',data,pe+6)[0]
opt=pe+24; imgbase=struct.unpack_from('<I',data,opt+28)[0]
secoff=opt+struct.unpack_from('<H',data,pe+20)[0]
secs=[]
for i in range(nsec):
    o=secoff+i*40
    vsize,vaddr,rawsize,rawptr=struct.unpack_from('<IIII',data,o+8)
    secs.append((vaddr,vsize,rawptr,rawsize))
def rva2off(rva):
    for vaddr,vsize,rawptr,rawsize in secs:
        if vaddr<=rva<vaddr+rawsize: return rawptr+(rva-vaddr)
    return None
rva = 0xC78212 - imgbase
o = rva2off(rva)
print("RVA", hex(rva), "off", hex(o))
print("static bytes at 0xC78212:", data[o:o+8].hex())
print("expected file bytes      : 8a1408  (mov dl,[eax+ecx])")
