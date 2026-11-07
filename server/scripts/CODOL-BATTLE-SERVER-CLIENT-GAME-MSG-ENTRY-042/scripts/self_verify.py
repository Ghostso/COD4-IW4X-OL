# -*- coding: utf-8 -*-
"""042 self-verification: re-derive every key claim from raw image bytes. Read-only."""
import sys, os, io, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import raw, rd32, cstr
ROOT=C.ROOT
res=[]; ok=True
def chk(name, cond, detail):
    global ok
    res.append((name, "PASS" if cond else "FAIL", detail))
    if not cond: ok=False

# image identity
chk("image_sha256", hashlib.sha256(C._b).hexdigest()=="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045",
    hashlib.sha256(C._b).hexdigest())
chk("image_base", C.IB==0x400000, hex(C.IB))
# net-buffer strings
chk("s_netbuf_notenough", bytes(raw(0x99EE98,30)).startswith(b"; net-buffer NOT enough:"), cstr(0x99EE98,40))
chk("s_string_len_err", b"string length error" in bytes(raw(0x99EEF0,60)), "")
chk("s_wstring_len_err", b"wstring length error" in bytes(raw(0x99EF50,60)), "")
chk("s_unit_notenough", b"net-buffer NOT enough" in bytes(raw(0x99EFB8,70)), "")
chk("s_str_format_err", b"string from net-buffer format error" in bytes(raw(0x99F290,70)), "")
# refs into code section
CODE_LO,CODE_HI=0x1000,0x8a8000
import struct
code=C._b[CODE_LO:CODE_HI]
def refs_of(rva):
    va=C.IB+rva; pat=struct.pack("<I",va); out=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        out.append(CODE_LO+j); i=j+1
    return out
chk("ref_netbuf_notenough", refs_of(0x99EE98)==[0x87cddb], str([hex(x) for x in refs_of(0x99EE98)]))
chk("ref_unit_notenough", refs_of(0x99EFB8)==[0x87c80a,0x87decc], str([hex(x) for x in refs_of(0x99EFB8)]))
# reader entry bytes
chk("sizeinfo_entry", raw(0x87A890,4).hex()=="558bec51", raw(0x87A890,4).hex())
chk("sizeinfo_width2", raw(0x87A8D3,6).hex()=="81ff80000000", raw(0x87A8D3,6).hex())
chk("sizeinfo_width3", raw(0x87A8EF,6).hex()=="81ff00010000", raw(0x87A8EF,6).hex())
chk("sizeinfo_width4", raw(0x87A8FC,6).hex()=="81ff00000100", raw(0x87A8FC,6).hex())
chk("deser1_entry", raw(0x87C110,5).hex()=="b8f4170000", raw(0x87C110,5).hex())
chk("deser2_entry", raw(0x87D5A0,5).hex()=="b80c180000", raw(0x87D5A0,5).hex())
# TQOS dispatcher
chk("dispatcher_entry", raw(0x85E6F0,5).hex()=="b87c9d0000", raw(0x85E6F0,5).hex())
chk("dispatcher_typeread", raw(0x85E75A,4).hex()=="0fb74424", raw(0x85E75A,4).hex())
chk("dispatcher_sub2", raw(0x85E75F,3).hex()=="83e802", raw(0x85E75F,3).hex())
chk("dispatcher_je", raw(0x85E762,2).hex()=="744c", raw(0x85E762,2).hex())
chk("dispatcher_sub2b", raw(0x85E764,3).hex()=="83e802", raw(0x85E764,3).hex())
# TQOS owner strings
chk("tqos_cspkg", cstr(0x985AA4,20)==b"QOSCSPkg", cstr(0x985AA4,20))
chk("tqos_udp", cstr(0x985AB0,20)==b"udp://%s:%d", cstr(0x985AB0,20))
chk("tqos_helper", b"tqos_find_connd_by_ip fail" in bytes(raw(0x985AE0,40)), "")
# caller of deser1 is TQOS region
def callers(t):
    tv=C.IB+t; out=[]; i=CODE_LO
    while i<CODE_HI-5:
        if C._b[i]==0xE8:
            rel=struct.unpack("<i",C._b[i+1:i+5])[0]
            if (C.IB+i)+5+rel==tv: out.append(i)
        i+=1
    return out
chk("deser1_caller", callers(0x87C110)==[0x85D49D], str([hex(x) for x in callers(0x87C110)]))
# OOB command strings + refs
chk("oob_getchallenge_ref", refs_of(0x9BFD04)==[0x1C071F], str([hex(x) for x in refs_of(0x9BFD04)]))
chk("oob_connectresponse_ref", refs_of(0x9BFF0C)==[0x1C17B5], str([hex(x) for x in refs_of(0x9BFF0C)]))
# coverage / BLOCKED boundary
chk("image_size", len(C._b)==0x00A65000, hex(len(C._b)))
chk("recv_slot_unavailable", 0xCA84E8 >= len(C._b), "0xCA84E8 beyond image")
chk("code_section_present", CODE_HI<=len(C._b), "code section fully present")

lines=["# 042 self-verification — re-derived from raw image bytes (read-only)","","CHECK\tRESULT\tDETAIL"]
for n,r,d in res: lines.append("%s\t%s\t%s"%(n,r,str(d)[:120]))
lines.append(""); lines.append("OVERALL: %s"%("PASS" if ok else "FAIL"))
io.open(os.path.join(ROOT,"TEST_AND_VALIDATION_RESULTS.md"),"w",encoding="utf-8",newline="").write("\n".join(lines)+"\n")
print("\n".join(lines))
