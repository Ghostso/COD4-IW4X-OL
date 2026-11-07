import struct
exe = r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
data = open(exe,'rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe+6)[0]
opt = pe+24
imgbase = struct.unpack_from('<I', data, opt+28)[0]
ddoff = opt + 96   # data directories start at opt+96
imp_rva, imp_size = struct.unpack_from('<II', data, ddoff + 1*8)
secoff = opt + struct.unpack_from('<H', data, pe+20)[0]
secs=[]
for i in range(nsec):
    o = secoff + i*40
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, o+8)
    secs.append((vaddr, vsize, rawptr, rawsize))
def rva2off(rva):
    for vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr+max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    return None
target = 0xCA8128 - imgbase   # RVA
print("target RVA", hex(target))
o = rva2off(imp_rva)
name = None
while True:
    oft, tstamp, fwd, namerva, firstthunk = struct.unpack_from('<IIIII', data, o)
    if namerva == 0 and firstthunk == 0: break
    dn = data[rva2off(namerva):rva2off(namerva)+64].split(b'\x00')[0].decode('latin1')
    # walk the thunk table
    t = rva2off(oft if oft else firstthunk)
    idx = 0
    while True:
        ent = struct.unpack_from('<I', data, t + idx*4)[0]
        if ent == 0: break
        slot_rva = firstthunk + idx*4
        if slot_rva == target:
            if ent & 0x80000000:
                print("DLL", dn, "ordinal", ent & 0xFFFF)
            else:
                fn = data[rva2off(ent)+2:rva2off(ent)+64].split(b'\x00')[0].decode('latin1')
                print("DLL", dn, "->", fn)
            name = dn
            break
        idx += 1
    if name: break
    o += 20
