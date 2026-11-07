# -*- coding: utf-8 -*-
"""Find all imm32 code references (in unpacked image) to net-message strings.
Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C

names = {
 b"CG_ServerCommand: ":"CG_ServerCommand",
 b"gamestateupdate %d":"gamestateupdate",
 b"getchallenge 0 \"%s\"":"getchallenge",
 b"connect %s \"%s\"":"connect_cmd",
 b"connectResponse":"connectResponse",
 b"challengeResponse":"challengeResponse",
 b"heartbeatresponse":"heartbeatresponse",
 b"statResponse":"statResponse",
 b"disconnect_ack":"disconnect_ack",
 b"keyAuthorize":"keyAuthorize",
 b"loadingnewmap":"loadingnewmap",
 b"uploadStats":"uploadStats",
 b"fastrestart":"fastrestart",
 b"userinfo \"%s\"":"userinfo",
 b"cancelConnect":"cancelConnect",
 b"ExpectedNetConfigStringMismatch":"ExpectedNetConfigStringMismatch",
 b"EXE_CONFIGSTRINGMISMATCH":"EXE_CONFIGSTRINGMISMATCH",
 b"EXE_POSSIBLECONFIGSTRINGMISMATCH":"EXE_POSSIBLECONFIGSTRINGMISMATCH",
 b"EXE_ERR_RELIABLE_CYCLED_OUT":"EXE_ERR_RELIABLE_CYCLED_OUT",
 b"EXE_ERR_NOT_RECEIVED":"EXE_ERR_NOT_RECEIVED",
 b"natType":"natType",
 b"secureProfileReady":"secureProfileReady",
}
targets={}
for kw,label in names.items():
    j=C._b.find(kw)
    if j<0: 
        print("  MISSING:", label); continue
    # VA = IB + offset
    targets[label]=(j, C.IB+j)

# build multiset of .text bytes for refs (code section = first .tp3 RVA 0x1000..0x8a8000)
code_lo, code_hi = 0x1000, 0x8a8000
code = C._b[code_lo:code_hi]
def refs_in_code(va):
    pat=struct.pack("<I",va); out=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        # require it be an operand position (roughly after a mov/push opcode); collect as-is
        out.append(code_lo+j); i=j+1
    return out

print("=== imm32 refs inside first .tp3 code ===")
allrefs={}
for label,(off,va) in sorted(targets.items()):
    r=refs_in_code(va)
    allrefs[label]=r
    print("  %-34s VA=%08x  refs=%s" % (label, va, [hex(x) for x in r[:10]]))
import json
json.dump({k:[hex(x) for x in v] for k,v in allrefs.items()},
          open(os.path.join(C.EV,"netstring_refs.json"),"w"), indent=2)
print("wrote netstring_refs.json")
