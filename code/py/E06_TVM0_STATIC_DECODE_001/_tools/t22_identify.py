import struct, io, re
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\lasttp3_blocks.bin"
d=open(p,"rb").read()
offs=[]; o=0
while True:
    i=d.find(b"MZ",o)
    if i<0: break
    o=i+1
    e,=struct.unpack_from("<I",d,i+0x3C) if i+0x40<=len(d) else (0,)
    if 0x40<=e<=0x400 and d[i+e:i+e+4]==b"PE\x00\x00": offs.append(i)
offs.append(len(d))
print("=== identify embedded modules: imports + version/export hints ===")
for n in range(len(offs)-1):
    i=offs[n]; end=offs[n+1]
    blob=d[i:end]
    # imports: scan for common DLL names
    dlls=sorted(set(re.findall(rb"[A-Za-z0-9_\-\.]{3,32}\.dll", blob)))
    # version strings
    ver=re.findall(rb"(?:FileDescription|ProductName|OriginalFilename|CompanyName|InternalName)[\x00]{0,3}[^\x00]{2,120}", blob)
    desc=re.findall(rb"[\x20-\x7e]{8,80}", blob)
    print("--- module %d: MZ@0x%X size=0x%X ---" % (n,i,len(blob)))
    print("    dll names: %s" % [x.decode('latin1') for x in dlls[:14]])
    vs=[x for x in desc if any(k in x for k in (b"TenProtect",b"VMProtect",b"TP3",b"tessafe",b"TenSafe",b"TenSafe",b"Tencent",b"CODOL",b"Call of Duty",b"Anti",b"protect"))]
    if vs:
        print("    notable strings: %s" % [x[:80].decode('latin1') for x in vs[:8]])
    # any version resource with VS_FIXEDFILEINFO
    if b"V\x00S\x00_\x00V\x00E\x00R\x00S\x00I\x00O\x00N" in blob: print("    has VS_VERSION_INFO")