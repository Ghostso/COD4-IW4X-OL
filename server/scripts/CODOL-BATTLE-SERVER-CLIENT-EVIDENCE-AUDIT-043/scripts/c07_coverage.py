# -*- coding: utf-8 -*-
"""Phase C: coverage/blocker audit - list which referenced addresses are inside the
recovered image vs outside; IAT slot resolution limits. Read-only."""
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def emit(s): out.append(s)
IMG_LEN=len(C._bi)
emit("=== recovered image coverage: RVA vs present ===")
emit("  file size 0x%X ; ImageBase 0x%X ; SizeOfImage 0x%X"%(IMG_LEN,C.IBI,C.pe_i.OPTIONAL_HEADER.SizeOfImage))
for s in C.pe_i.sections:
    va=s.VirtualAddress; vs=s.Misc_VirtualSize; raw=s.PointerToRawData; rs=s.SizeOfRawData
    present = (raw+rs)<=IMG_LEN
    emit("  %-10s VA=%08X VSize=%08X raw=%08X rsize=%08X %s"%(
        s.Name.rstrip(b'\0').decode('latin1'),va,vs,raw,rs,"FULL" if present else "PARTIAL/ABSENT"))

emit("")
emit("=== critical addresses used by 042 conclusions ===")
crit={
 "netbuf read primitive 0x87BE00 entry":0x87BE00,
 "read API slot 0xCA84E8":0xCA84E8,
 "read API slot 0xCA84E4":0xCA84E4,
 "last-error slot 0xCA853C":0xCA853C,
 "netbuf sizeinfo 0x87A890":0x87A890,
 "netbuf deser1 0x87C110":0x87C110,
 "netbuf deser2 0x87D5A0":0x87D5A0,
 "shared core 0x87ED70":0x87ED70,
 "TQOS dispatcher 0x85E6F0":0x85E6F0,
 "global 0x76446B0 (dispatcher state)":0x76446B0,
 "global 0x84ABB08":0x84ABB08,
 "global 0xE3F240 (security cookie)":0xE3F240,
 "net-buffer string 0x99EE98":0x99EE98,
}
for k,v in crit.items():
    inside = v < IMG_LEN
    emit("  %-40s RVA=%08X %s"%(k,v,"IN-IMAGE" if inside else "OUT-OF-IMAGE -> BLOCKED"))

emit("")
emit("=== note: IAT slots 0xCAxxxx are far outside image (need higher sections) ===")
io.open(os.path.join(C.EV,"c_coverage_blockers.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
