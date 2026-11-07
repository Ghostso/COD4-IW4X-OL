import struct, re
for name in [r"run_codol_001\sandbox_ifs1_20260923\TCJ.dll",
             r"run_codol_001\sandbox_ifs1_20260923\TenProxy.dll"]:
    try:
        d = open(name,"rb").read()
    except OSError:
        print(name, "MISSING"); continue
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe+6)[0]
    optsz = struct.unpack_from("<H", d, pe+20)[0]
    optoff = pe+24
    magic = struct.unpack_from("<H", d, optoff)[0]
    ddoff = optoff + (96 if magic==0x10B else 112)
    exp_rva,_ = struct.unpack_from("<II", d, ddoff)
    secs=[]; so=optoff+optsz
    for i in range(nsec):
        vsize,vaddr,rsize,raddr = struct.unpack_from("<IIII", d, so+i*40+8)
        secs.append((vaddr,vsize,raddr,rsize))
    def r2o(rva):
        for va,vs,ra,rs in secs:
            if va <= rva < va+max(vs,rs): return ra+(rva-va)
        return None
    eo = r2o(exp_rva) if exp_rva else None
    print("=== %s (size=%d) ===" % (name.split("\\")[-1], len(d)))
    if eo:
        nfun = struct.unpack_from("<I", d, eo+0x14)[0]
        anp = r2o(struct.unpack_from("<I", d, eo+0x20)[0])
        names=[]
        for i in range(min(nfun,25)):
            no = r2o(struct.unpack_from("<I", d, anp+i*4)[0])
            if no:
                end = d.index(b"\x00", no)
                try: names.append(d[no:end].decode("ascii"))
                except Exception: names.append("?")
        print("  exports(%d): %s" % (nfun, names))
    # tas hints
    hits = set()
    for m in re.finditer(rb"[\x20-\x7E]{6,80}", d):
        s = m.group().decode("ascii","ignore")
        if re.search(r"tas|TAS|TenProtect|tenio|TP3|dsa|DSA", s):
            hits.add(s[:70])
    for s in sorted(hits)[:15]: print("  str:", s)
