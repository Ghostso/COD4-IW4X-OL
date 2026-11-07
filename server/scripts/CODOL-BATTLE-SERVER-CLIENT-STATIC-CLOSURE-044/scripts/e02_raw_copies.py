# -*- coding: utf-8 -*-
"""044: inspect ALL image_best.bin copies as raw bytes (no PE assumption).
Question: does ANY existing copy contain nonzero bytes at file offset 0xCA84E8
(which under file_offset==RVA would be the recv-like read API slot)? READ-ONLY."""
import _common as c, os, hashlib, struct

out=[]
def P(s=""): out.append(s)

copies=[]
for base,dirs,files in os.walk(c.WS):
    for fn in files:
        if fn.lower()=="image_best.bin":
            copies.append(os.path.join(base,fn))
P("copies = %d"%len(copies))
P("")
P("## raw probe: bytes at offset 0xCA84E8 / 0xCA84E4 / 0xCA853C and file MZ/PE header")
for path in sorted(copies):
    try:
        with open(path,"rb") as f: b=f.read()
    except OSError as e:
        P("  ERR %s"%path); continue
    h=hashlib.sha256(b).hexdigest()
    mz=b[:2]
    off_pe=struct.unpack("<I",b[0x3c:0x40])[0] if len(b)>0x40 else None
    def q(o):
        return b[o:o+4].hex() if o+4<=len(b) else "OOB"
    P("  %s size=%d mz=%r pe_off=%s"%(h[:16]+"...",len(b),mz,hex(off_pe) if off_pe is not None else None))
    P("      path=%s"%path)
    P("      @0xCA84E8=%s  @0xCA84E4=%s  @0xCA853C=%s  @0xCA8510=%s"%(q(0xCA84E8),q(0xCA84E4),q(0xCA853C),q(0xCA8510)))
P("")

# Also: search each copy for the ASCII import name 'recv' / 'WSARecv' near any IAT-like
P("## import-name strings present in each copy (whole-file ASCII search)")
for path in sorted(copies):
    with open(path,"rb") as f: b=f.read()
    h=hashlib.sha256(b).hexdigest()[:16]
    found=[]
    for name in (b"recv",b"WSARecv",b"recvfrom",b"WSAGetLastError",b"select",b"WSAPoll",b"WSARecvFrom"):
        idx=b.find(name)
        if idx>=0: found.append("%s@%x"%(name.decode(),idx))
    P("  %s  %s"%(h,found if found else "(none)"))
c.w(os.path.join(c.EV,"e02_raw_copies.txt"),"\n".join(out))
print("\n".join(out))