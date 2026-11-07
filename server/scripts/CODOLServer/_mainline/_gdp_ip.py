import pefile, re, struct
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
# 谁引用 183.60.58.99 (VA 0x10037428)
i=d.find(b"183.60.58.99")
va=ib+pe.get_rva_from_offset(i)
print("183.60.58.99 @ VA 0x%08X"%va)
le=struct.pack("<I",va); hits=[]; s=0
while True:
    j=d.find(le,s)
    if j<0: break
    hits.append(ib+pe.get_rva_from_offset(j)); s=j+1
print("引用点:", [hex(x) for x in hits])
# inet_addr 形式 (0x633c3cb7)
be=struct.pack("<I", struct.unpack(">I", bytes([183,60,58,99]))[0])
h2=[]; s=0
while True:
    j=d.find(be,s)
    if j<0: break
    h2.append(ib+pe.get_rva_from_offset(j)); s=j+1
print("inet_addr(0x%08X) 命中: %s"%(struct.unpack("<I",be)[0],[hex(x) for x in h2]))
print()
# GDP protocol 内部方法名
print("=== 含 Qos 的完整名字列表 ===")
for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{3,70}", d):
    s2=m.group().decode("latin1")
    if "Qos" in s2 or "QOS" in s2:
        print("   VA 0x%08X %s"%(ib+pe.get_rva_from_offset(m.start()), s2))
