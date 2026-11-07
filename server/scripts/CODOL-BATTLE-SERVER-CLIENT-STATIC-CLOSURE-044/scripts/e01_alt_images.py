# -*- coding: utf-8 -*-
"""044 Phase E: can any *other already-existing* recovery image resolve the IAT slot
0xCA84E8 (BE-01) without new runtime capture? READ-ONLY."""
import _common as c, os, hashlib, pefile, struct

out=[]
def P(s=""): out.append(s)

copies=[]
for base,dirs,files in os.walk(c.WS):
    for fn in files:
        if fn.lower()=="image_best.bin":
            copies.append(os.path.join(base,fn))
P("# all image_best.bin copies on disk = %d"%len(copies))

def probe(path):
    with open(path,"rb") as f: b=f.read()
    try:
        pe=pefile.PE(data=b,fast_load=False)
    except Exception:
        return None
    secs=[dict(name=s.Name.rstrip(b"\0").decode("latin1"),va=s.VirtualAddress,
               vsize=s.Misc_VirtualSize,raw=s.PointerToRawData,rsize=s.SizeOfRawData) for s in pe.sections]
    return dict(buf=b,hash=hashlib.sha256(b).hexdigest(),size=len(b),
                ib=pe.OPTIONAL_HEADER.ImageBase, ts=pe.FILE_HEADER.TimeDateStamp,
                ep=pe.OPTIONAL_HEADER.AddressOfEntryPoint, secs=secs)

def present(r,rva,n):
    b=r["buf"]
    if rva<0 or rva+n>len(b): return None
    for s in r["secs"]:
        if s["raw"]<=rva and rva+n<=s["raw"]+s["rsize"]:
            return b[rva:rva+n]
    return None

targets={0xCA84E8:"read-API slot A",0xCA84E4:"read-API slot B",0xCA853C:"last-error slot",
         0xCA8510:"slot fed to jmp[0xca8510]",0xCA8330:"alloc slot (used by 0x87ED70)"}

P("")
P("## distinct builds (deduplicated by full SHA-256) and IAT-region presence")
seen=set()
for path in sorted(copies):
    r=probe(path)
    if r is None:
        P("!! unparsable: %s"%path); continue
    if r["hash"] in seen: continue
    seen.add(r["hash"])
    P("="*92)
    P("build %s size=%d TS=%08x EP=%08x IB=%08x"%(r["hash"],r["size"],r["ts"],r["ep"],r["ib"]))
    P("  %s"%path)
    # coverage of the low part of section that contains 0xCA84E8
    sec_of=None
    for i,s in enumerate(r["secs"]):
        if s["va"]<=0x0CA84E8<s["va"]+max(s["vsize"],s["rsize"]):
            sec_of=(i,s)
    if sec_of:
        i,s=sec_of
        P("  IAT-containing sec #%d name=%r VA=%08x VSize=%08x raw=%08x rsize=%08x"%(i,s["name"],s["va"],s["vsize"],s["raw"],s["rsize"]))
    got=False
    for t,label in targets.items():
        pb=present(r,t,4)
        if pb is not None:
            got=True
            val=struct.unpack("<I",pb)[0]
            P("   %08x %-28s = %s  (0x%08x)"%(t,label,pb.hex(),val))
    if not got:
        P("   [none of the target IAT slots are present in this build]")
P("")
c.w(os.path.join(c.EV,"e01_alt_images.txt"),"\n".join(out))
print("\n".join(out))