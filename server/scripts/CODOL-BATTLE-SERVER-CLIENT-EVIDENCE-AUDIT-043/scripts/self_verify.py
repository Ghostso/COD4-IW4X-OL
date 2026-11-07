# -*- coding: utf-8 -*-
"""043 self-verification: re-derive the audited claims from raw bytes. Read-only."""
import sys, os, io, hashlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT; res=[]; ok=True
def chk(n,cond,d):
    global ok
    res.append((n,"PASS" if cond else "FAIL",str(d)[:120]))
    if not cond: ok=False

# identities
chk("sha_dll", C.sha256_file(C.DLL)=="ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20", C.sha256_file(C.DLL))
chk("sha_exe", C.sha256_file(C.EXE)=="36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537", C.sha256_file(C.EXE))
chk("sha_img", C.sha256_file(C.IMG)=="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045", C.sha256_file(C.IMG))
# convention
chk("conv_gamestate", C._bi[0x9B4700:0x9B4700+15]==b"gamestateupdate", C._bi[0x9B4700:0x9B4700+17])
chk("conv_connectResponse", C._bi[0x9BFF0C:0x9BFF0C+15]==b"connectResponse", C._bi[0x9BFF0C:0x9BFF0C+15])
chk("conv_cgservercommand", C._bi[0x9C61AD:0x9C61AD+16]==b"CG_ServerCommand", C._bi[0x9C61AD:0x9C61AD+17])
chk("conv_netbuffer_str", C._bi[0x99EE98:0x99EE98+23]==bytes.fromhex("3b206e65742d627566666572204e4f5420656e6f756768"), C._bi[0x99EE98:0x99EE98+23].hex())
# EXE/IMG same EP
chk("exe_img_same_ep", C.pe_i.OPTIONAL_HEADER.AddressOfEntryPoint==0x0E5DC690, hex(C.pe_i.OPTIONAL_HEADER.AddressOfEntryPoint))
chk("exe_img_same_ts", C.pe_i.FILE_HEADER.TimeDateStamp==0x6096930A, hex(C.pe_i.FILE_HEADER.TimeDateStamp))
# image coverage
chk("img_len", len(C._bi)==0xA65000, hex(len(C._bi)))
chk("iat_out_of_image", 0xCA84E8>=len(C._bi), "0xCA84E8 beyond")
# 0x87A890 writes sizeinfo tag 0xC
chk("encoder_tag_0C", C._bi[0x87A92F:0x87A931]==b"\xc6\x03", C._bi[0x87A92F:0x87A931].hex())
chk("encoder_threshold_0x80", C._bi[0x87A8D3:0x87A8D9]==b"\x81\xff\x80\x00\x00\x00", C._bi[0x87A8D3:0x87A8D9].hex())
chk("encoder_threshold_0x100", C._bi[0x87A8EF:0x87A8F5]==b"\x81\xff\x00\x01\x00\x00", C._bi[0x87A8EF:0x87A8F5].hex())
chk("encoder_threshold_0x10000", C._bi[0x87A8FC:0x87A902]==b"\x81\xff\x00\x00\x01\x00", C._bi[0x87A8FC:0x87A902].hex())
# 0x744B20 always returns 1
chk("helper_744b20_true", C._bi[0x744B20:0x744B26]==b"\xb8\x01\x00\x00\x00\xc3", C._bi[0x744B20:0x744B26].hex())
# 0x87C110 has only 2 [ebx+8]
cnt=0
for k in C.idis_range(0x87C110,0x87D593):
    if "[ebx + 8]" in k.op_str: cnt+=1
chk("deser_ebx8_count_2", cnt==2, cnt)
# 0x87D5A0 dual buffer reads
chk("deser2_reads_buf", C._bi[0x87D60F:0x87D611]==b"\x8b\x33", C._bi[0x87D60F:0x87D611].hex())
# callers
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if C._bi[i]==0xE8:
            rel=struct.unpack("<i",C._bi[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
chk("deser1_caller", callers(0x87C110)==[0x85D49D], [hex(x) for x in callers(0x87C110)])
chk("deser2_callers", callers(0x87D5A0)==[0x85D3DB,0x85D418,0x85D9B5,0x85D9F7], [hex(x) for x in callers(0x87D5A0)])
chk("encoder_caller", callers(0x87A890)==[0x879CE3], [hex(x) for x in callers(0x87A890)])
# string refs
code=C._bi[0x1000:0x8a8000]
def refs_of(rva):
    va=C.IBI+rva; pat=struct.pack("<I",va); rr=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        rr.append(0x1000+j); i=j+1
    return rr
chk("ref_netbuf_real_len", refs_of(0x99EE98)==[0x87CDDB], [hex(x) for x in refs_of(0x99EE98)])
chk("ref_unit_size", refs_of(0x99EFB8)==[0x87C80A,0x87DECC], [hex(x) for x in refs_of(0x99EFB8)])
chk("ref_wstring_fmt", refs_of(0x99F428)==[0x87E306], [hex(x) for x in refs_of(0x99F428)])
# TQOS string binding
chk("tqos_cspkg_ref", refs_of(0x985AA4)==[0x85D2F6], [hex(x) for x in refs_of(0x985AA4)])
chk("tqos_udp_ref", set(refs_of(0x985AB0))=={0x85D7CB,0x85D89A}, [hex(x) for x in refs_of(0x985AB0)])
chk("tqos_create_err_ref", refs_of(0x985B1C)==[0x85EBD0], [hex(x) for x in refs_of(0x985B1C)])
# dispatcher type read + branch
chk("dispatcher_typeread", C._bi[0x85E75A:0x85E75E].hex()=="0fb74424", C._bi[0x85E75A:0x85E75E].hex())
chk("dispatcher_sub2", C._bi[0x85E75F:0x85E762].hex()=="83e802", C._bi[0x85E75F:0x85E762].hex())
# 0x87D5A0 != wrapper of 0x87C110
chk("deser_entries_independent", C._bi[0x87C110:0x87C115].hex()=="b8f4170000" and C._bi[0x87D5A0:0x87D5A5].hex()=="b80c180000",
    C._bi[0x87C110:0x87C115].hex()+"/"+C._bi[0x87D5A0:0x87D5A5].hex())

lines=["# 043 self-verification — re-derived from raw bytes (read-only)","","CHECK\tRESULT\tDETAIL"]
for n,r,d in res: lines.append("%s\t%s\t%s"%(n,r,d))
lines+= ["","OVERALL: %s"%("PASS" if ok else "FAIL")]
io.open(os.path.join(ROOT,"TEST_AND_VALIDATION_RESULTS.md"),"w",encoding="utf-8",newline="").write("\n".join(lines)+"\n")
print("\n".join(lines))
