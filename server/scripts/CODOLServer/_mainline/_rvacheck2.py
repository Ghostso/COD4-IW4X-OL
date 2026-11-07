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
    name=data[o:o+8].rstrip(b'\x00').decode('latin1')
    vsize,vaddr,rawsize,rawptr=struct.unpack_from('<IIII',data,o+8)
    secs.append((name,vaddr,vsize,rawptr,rawsize))
# two conventions: RVA-space (vaddr is RVA) and VA-space
def rva2off(rva):
    for name,vaddr,vsize,rawptr,rawsize in secs:
        if vaddr<=rva<vaddr+rawsize: return name, rawptr+(rva-vaddr)
    return None,None
print("imagebase", hex(imgbase))
for rva in (0x95520, 0x95514, 0x5A4E0, 0x5A4E8):
    n,o = rva2off(rva)
    print("RVA %06X -> %s off %s  %s" % (rva, n, hex(o) if o else None, data[o:o+24].hex() if o else ""))
