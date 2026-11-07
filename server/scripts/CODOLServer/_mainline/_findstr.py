import struct
exe = r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
data = open(exe,'rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe+6)[0]
opt = pe+24
imgbase = struct.unpack_from('<I', data, opt+28)[0]
secoff = opt + struct.unpack_from('<H', data, pe+20)[0]
secs=[]
for i in range(nsec):
    o = secoff + i*40
    name = data[o:o+8].rstrip(b'\x00').decode('latin1')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, o+8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))
    if rawsize < vsize:
        pass
print("sections:")
for s in secs: print("  %-10s va=%08X vsize=%08X raw=%08X" % (s[0], s[1], s[2], s[4]))

def va2off(va):
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= va < vaddr+rawsize:
            return rawptr + (va-vaddr)
    return None

# find "CLIENTCHAL" occurrences anywhere in the file
for pat in (b"CLIENTCHAL", b"BDDDATA", b"HMAC mismatch"):
    offs=[]
    i=0
    while True:
        j=data.find(pat,i)
        if j<0: break
        offs.append(j); i=j+1
    out=[]
    for o in offs:
        for name, vaddr, vsize, rawptr, rawsize in secs:
            if rawptr <= o < rawptr+rawsize:
                out.append((hex(vaddr+(o-rawptr)), name))
    print(pat, "count", len(offs), out[:10])
