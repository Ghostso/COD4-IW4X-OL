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
def rva2off(rva):
    for name,vaddr,vsize,rawptr,rawsize in secs:
        if vaddr<=rva<vaddr+rawsize: return name, rawptr+(rva-vaddr)
    return None,None
for rva in (0x995520, 0x995514):
    n,o=rva2off(rva)
    print("=== RVA %06X (%s) ===" % (rva,n))
    b=data[o:o+64]
    for k in range(0,64,4):
        print("   +0x%02X = 0x%08X" % (k, struct.unpack_from('<I',b,k)[0]))
