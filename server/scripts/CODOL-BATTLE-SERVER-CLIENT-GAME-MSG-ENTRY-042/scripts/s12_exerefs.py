# -*- coding: utf-8 -*-
"""Find code references to the EXE net-command string table. Read-only."""
import sys, os, struct, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
pe=pefile.PE(data=data, fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase
SECS=[]
for s in pe.sections:
    SECS.append((s.VirtualAddress, s.VirtualAddress+s.Misc_VirtualSize, s.PointerToRawData,
                 s.PointerToRawData+s.SizeOfRawData, s.Name.rstrip(b'\0').decode('latin1'), s.Characteristics))
def rva2off(r):
    for va,ve,raw,rend,nm,ch in SECS:
        if va<=r<max(ve, raw and (va+(rend-raw)) or ve):
            if raw<= raw+(r-va) < rend: return raw+(r-va)
    # fallback simple
    for va,ve,raw,rend,nm,ch in SECS:
        if va<=r<ve and raw+(r-va)<rend: return raw+(r-va)
    return None
def off2rva(o):
    for va,ve,raw,rend,nm,ch in SECS:
        if raw<=o<rend: return va+(o-raw)
    return None

# gather net strings & their RVAs
targets={}
for s in (b"connectResponse",b"connectReject",b"challengeResponse",b"heartbeatresponse",
          b"statResponse",b"disconnect_ack",b"keyAuthorize",b"gamestateupdate",
          b"CG_ServerCommand: ",b"loadingnewmap",b"uploadStats",b"fastrestart",
          b"getchallenge 0 \"%s\"",b"connect %s \"%s\""):
    j=data.find(s)
    if j<0: continue
    r=off2rva(j)
    if r is None: continue
    targets[s.decode('latin1')]=(r, ib+r)

print("=== target strings (RVA / VA) ===")
for k,(r,va) in targets.items():
    print("  %-24s RVA=%08x VA=%08x" % (k, r, va))

# scan whole file for little-endian imm32 == VA (code refs)
print("\n=== imm32 references (anywhere in file) ===")
for k,(r,va) in targets.items():
    pat=struct.pack("<I",va); hits=[]; i=0
    while True:
        j=data.find(pat,i)
        if j<0: break
        rr=off2rva(j); hits.append((j, rr)); i=j+1
    print("  %-24s : %s" % (k, [ (hex(o), hex(rr) if rr is not None else None) for o,rr in hits[:8]]))

# Check if first .tp3 is x86 code
print("\n=== section characteristics ===")
for va,ve,raw,rend,nm,ch in SECS:
    print("  %-8s rva=%08x vsize=%08x raw=%08x rsize=%08x chars=%08x %s" %
          (nm, va, ve-va, raw, rend-raw, ch, "CODE" if ch & 0x20 else "DATA"))
