import struct, sys

def parse_strings(path):
    d = open(path,"rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe+6)[0]
    optsz = struct.unpack_from("<H", d, pe+20)[0]
    optoff = pe + 24
    magic = struct.unpack_from("<H", d, optoff)[0]
    ddoff = optoff + (96 if magic == 0x10B else 112)
    rva_meta, size_meta = struct.unpack_from("<II", d, ddoff + 14*8)
    # find section containing rva_meta
    secs = []
    so = optoff + optsz
    for i in range(nsec):
        name = d[so+i*40: so+i*40+8].rstrip(b"\x00")
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", d, so+i*40+8)
        secs.append((name, vaddr, vsize, raddr, rsize))
    def r2o(rva):
        for name, vaddr, vsize, raddr, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raddr + (rva - vaddr)
        return None
    mo = r2o(rva_meta)
    if mo is None: return None, None
    # metadata root
    sig, maj, minr, res, verlen = struct.unpack_from("<IHHII", d, mo)
    p = mo + 16 + verlen
    p += 2  # flags
    nstreams = struct.unpack_from("<H", d, p)[0]; p += 2
    streams = {}
    for _ in range(nstreams):
        off, sz = struct.unpack_from("<II", d, p); p += 8
        q = p
        while d[q] != 0: q += 1
        nm = d[p:q].decode("ascii","replace"); p = q + 1
        p = (p + 3) & ~3
        streams[nm] = (mo + off, sz)
    return streams, d

for path,label in [(r"backups\FROZEN_20261002_222802\A_observer_out\AboProbe.dll","50176"),
                   (r"restore_iips_contract_001\observer2\uut3\AboProbe.dll","90624")]:
    st, d = parse_strings(path)
    if not st:
        print(label, "parse failed"); continue
    (so, ss) = st.get("#Strings", (None,None))
    (bo, bs) = st.get("#~", (None,None))
    strs = d[so:so+ss]
    # count NUL-separated names
    names = [x for x in strs.split(b"\x00") if x]
    print("%s: #Strings=%d bytes, %d names, #~=%d bytes" % (label, ss, len(names), bs))
