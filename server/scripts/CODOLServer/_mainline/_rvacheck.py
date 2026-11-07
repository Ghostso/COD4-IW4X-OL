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
    secs.append((vaddr,rawsize,rawptr))
def va2off(va):
    for vaddr,rawsize,rawptr in secs:
        if vaddr<=va<vaddr+rawsize: return rawptr+(va-vaddr)
    return None
print("imagebase", hex(imgbase))
for va in (0xD95520, 0xD95514, 0xD5A4E0, 0xD5A4E8, 0xD95528):
    o=va2off(va)
    print(hex(va), "fileoff", hex(o) if o else None, data[o:o+32].hex() if o else "")
