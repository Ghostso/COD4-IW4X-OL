# -*- coding: utf-8 -*-
"""041 self-verification: re-derive every key claim from raw bytes. Read-only."""
import sys, os, io, hashlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
ROOT=C.ROOT
res=[]; ok=True
def chk(name, cond, detail):
    global ok
    res.append((name, "PASS" if cond else "FAIL", detail))
    if not cond: ok=False

# 1. DLL hash
h = hashlib.sha256(C._b).hexdigest()
chk("dll_sha256", h=="ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20", h)

# 2. recvfrom call bytes + slot
chk("recv_call_bytes", raw(0x235F7E,6).hex()=="ff15482ab010", raw(0x235F7E,6).hex())
v=rd32(0xB02A48); chk("recvfrom_slot_ordinal17", (v&0x80000000) and (v&0xffff)==17, hex(v))

# 3. WSASocketW unique + args
import re
def tgt15(ins):
    m=re.search(r"\[(0x[0-9a-f]+)\]",ins.op_str); return int(m.group(1),16) if m else None
ff=scan_ff15()
ws=[i.address-IB for i in ff if tgt15(i)==IB+0xB02A60]
chk("wsasocketw_unique", ws==[0x235D6D], str([hex(x) for x in ws]))
# args: push 0,0,0,1,3,2 just before
argb=raw(0x235D5E,12).hex()
chk("wsasocketw_args", argb=="6a006a006a006a016a036a02", argb)

# 4. ICMP type 8 write
chk("icmp_type8", raw(0x235E8D,3).hex()=="c60708", raw(0x235E8D,3).hex())
# seq write, id write
chk("icmp_id_write", raw(0x235E97,3).hex()=="894f04", raw(0x235E97,3).hex())
chk("icmp_seq_write", raw(0x235E9A,4).hex()=="66895f08", raw(0x235E9A,4).hex())
chk("icmp_ts_write", raw(0x235E9E,3).hex()=="89570c", raw(0x235E9E,3).hex())
# checksum helper loop count 6
chk("checksum_loop6", raw(0x2360BF,7).hex()=="c745fc06000000", raw(0x2360BF,7).hex())
chk("checksum_not", raw(0x2360FF,2).hex()=="f7d0", raw(0x2360FF,2).hex())

# 5. sendto call + len 0x30
chk("sendto_call", raw(0x235EC9,6).hex()=="ff154c2ab010", raw(0x235EC9,6).hex())
chk("sendto_len30", raw(0x235EC5,2).hex()=="6a30", raw(0x235EC5,2).hex())

# 6. recv buffer private + no copy: only 2 lea/mov refs to [ebp-0x10C]
refs=[]
for i in dis_range(0x235E00,0x2360B0):
    if "ebp - 0x10c" in i.op_str: refs.append((i.address-IB,i.mnemonic,i.op_str))
chk("buf_ref_count_3", len(refs)==3, str([(hex(a),m) for a,m,_ in refs]))
# no memcpy-like opcodes (rep movs / movsd / movsb) in function
body=raw(0x235E00,0x2360B0-0x235E00)
chk("no_rep_movs", (b"\xf3\xa4" not in body) and (b"\xf3\xa5" not in body) and (b"\xa4" not in body), "no movs/movsb")

# 7. IHL parse
chk("ihl_and0f", raw(0x235F94,7).hex()=="8a8df4feffff80", raw(0x235F94,7).hex())
chk("ihl_shl2", raw(0x235FA1,6).hex()=="6603d26603d2", raw(0x235FA1,6).hex())

# 8. type==0 check
chk("type0_check", raw(0x235FC0,3).hex()=="803900", raw(0x235FC0,3).hex())

# 9. out writes
chk("out_rtt_write", raw(0x236058,7).hex()=="2b410c8bb5e0fe", raw(0x236058,7).hex())
chk("out_seq_write", raw(0x236073,3).hex()=="66891e", raw(0x236073,3).hex())
chk("out_ttl_write", raw(0x236079,3).hex()=="894e0c", raw(0x236079,3).hex())
chk("ttl_read_buf8", raw(0x236061,7).hex()=="0fb68dfcfeffff", raw(0x236061,7).hex())
chk("plen_minus10", raw(0x236070,2).hex()=="83ef", raw(0x236070,2).hex())

# 10. return without copy
chk("return_zero", raw(0x23607C,2).hex()=="33c0", raw(0x23607C,2).hex())

# 11. caller: out stack slot + call
chk("caller_call", raw(0x2310E5,5).hex()=="e8164d0000", raw(0x2310E5,5).hex())
chk("caller_out_ptr", raw(0x2310DA,4).hex()=="8d442414", raw(0x2310DA,4).hex())
chk("caller_push_out", raw(0x2310DE,1).hex()=="50", raw(0x2310DE,1).hex())

# 12. CreateThread launcher
chk("createthread_call", raw(0x22D53C,6).hex()=="ff152c23b010", raw(0x22D53C,6).hex())
chk("lpstart_addr", raw(0x22D533,5).hex()=="6850102310", raw(0x22D533,5).hex())

# 13. thread proc unique dword ref
import struct
pat=struct.pack("<I",IB+0x231050); b=C._b
n=b.count(pat)
chk("threadproc_ref", n==1, "dword refs=%d"%n)

# 14. only one recvfrom in 0x235xxx cluster
recv_sites=[i.address-IB for i in ff if tgt15(i) in (IB+0xB02A48,IB+0xB02B3C)]
cluster=[x for x in recv_sites if 0x235000<=x<0x240000]
chk("cluster_recv_sites", cluster==[0x235F7E], str([hex(x) for x in recv_sites]))

# 15. .tvm0 upstream caller
# whole-file scan: caller of 0x22D470 lives in .tvm0 (outside .text)
import struct as _s
rel=[]; _bb=C._b
for _i in range(0,len(_bb)-5):
    if _bb[_i]==0xE8:
        _src=off2rva(_i)
        if _src is None: continue
        _t=IB+_src+5+_s.unpack("<i",_bb[_i+1:_i+5])[0]
        if _t==IB+0x22D470: rel.append(_src)
chk("launcher_upstream_sec", [sec_of_rva(x) for x in rel]==[".tvm0"], str([(hex(x),sec_of_rva(x)) for x in rel]))

# 16. caller frame map (path-sensitive ESP model) — corrected 2026-10-13
import frame_model as _FM
_ins,_esp=_FM.run()
_ob=sorted(_esp[0x2310DA])[0]+0x14
def _rel(a):
    return sorted({e+int(__import__("re").search(r"esp \+ (0x[0-9a-f]+)",_ins[a].op_str).group(1),16)-_ob for e in _esp[a]})
chk("frame_out_base_rel0", _rel(0x2310DA)==[0], str(_rel(0x2310DA)))
chk("frame_thisD_rel16", _rel(0x2310DF)==[16], str(_rel(0x2310DF)))
chk("frame_reader171_out04", _rel(0x231171)==[4], str(_rel(0x231171)))
chk("frame_reader175_out0C", _rel(0x231175)==[12], str(_rel(0x231175)))
chk("frame_D_socket_rel16", _rel(0x231112)==[16], str(_rel(0x231112)))
chk("frame_D_event_rel20", _rel(0x231129)==[20], str(_rel(0x231129)))
chk("frame_job4_from_out04", raw(0x231179,3).hex()=="894e04" and raw(0x231171,3).hex()=="8b4c24", raw(0x231171,3).hex())
chk("frame_job8_from_out0C", raw(0x23117c,3).hex()=="895608" and raw(0x231175,3).hex()=="8b5424", raw(0x231175,3).hex())

lines=["# 041 self-verification — re-derived from raw DLL bytes (read-only)","",
       "CHECK\tRESULT\tDETAIL"]
for n,r,d in res:
    lines.append("%s\t%s\t%s"%(n,r,d))
lines.append("")
lines.append("OVERALL: %s"%("PASS" if ok else "FAIL"))
io.open(os.path.join(ROOT,"TEST_AND_VALIDATION_RESULTS.md"),"w",encoding="utf-8",newline="").write("\n".join(lines)+"\n")
print("\n".join(lines))


