# -*- coding: utf-8 -*-
"""041 deliverable generator (read-only analysis outputs)."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

ROOT = C.ROOT
def W(name, text):
    io.open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="").write(text)

def bhex(rva, n):
    d = raw(rva, n)
    return d.hex() if d else ""

def ins(rva):
    i = dis_at(rva)
    return "%s %s" % (i.mnemonic, i.op_str) if i else "?"

# ============================================================ 03 OUT STRUCTURE FIELDS
tsv3 = ["FIELD_ID\tOFFSET\tSIZE\tFIELD_NAME\tSEMANTIC\tWRITE_RVA\tWRITE_INSN\tRAW_BYTES\tSOURCE_EXPR\tSOURCE_ORIGIN\tREADBACK\tCONFIDENCE\tNOTE"]
tsv3.append("OUT-000\t+0x00\t2\tseq\tICMP sequence echoed back / matched\t0x236073\t%s\t%s\tbx (=[esi+0x12] echo of request seq)\trequest seq counter obj+0x12\tcaller 0x231050 reads result into thread block\tCONFIRMED_DATAFLOW\tword write; equals ICMP field at buf[ihl*4+8]" % (ins(0x236073), bhex(0x236073,4)))
tsv3.append("OUT-004\t+0x04\t4\trtt\tround-trip time = now_tick - echoed_tick\t0x236068\t%s\t%s\teax = call 0x236110() - [ecx+0xC]\tnow (0x236110) minus echoed tick at buf[ihl*4+0xC]\tcaller 0x231050 result block\tCONFIRMED_DATAFLOW\techoed tick written at 0x235E9E from 0x236110" % (ins(0x236068), bhex(0x236068,4)))
tsv3.append("OUT-008\t+0x08\t4\tpayload_len\trecvlen - ihl*4 - 0x10\t0x236076\t%s\t%s\tedi = recvlen - (ihl*4) - 0x10\trecvfrom return EDI and IP IHL\tcaller 0x231050 result block\tCONFIRMED_DATAFLOW\tconstant 0x10 overhead assumption; no payload copy" % (ins(0x236076), bhex(0x236076,4)))
tsv3.append("OUT-00C\t+0x0C\t4\ttl\treply IP TTL (zero-extended)\t0x236079\t%s\t%s\tecx = movzx byte [ebp-0x104] = buf[8]\tIP header TTL byte (offset 8 of raw IP packet)\tcaller 0x231050 (path 0x231171) reads [esp+0x20]=out+0xC\tCONFIRMED_DATAFLOW\tIP TTL of the ICMP echo reply" % (ins(0x236079), bhex(0x236079,5)))
tsv3.append("OUT-010\t+0x10\t-\t(not part of out)\tcaller frame follows; D object begins at caller [esp+0x24]\t-\t-\t\t-\t-\tsocket/WSAEVENT teardown target\tCONFIRMED_DIRECT\tout region [esp+0x14..0x24); D object at [esp+0x24]" % ())
W("03_OUT_STRUCTURE_FIELDS.tsv", "\n".join(tsv3) + "\n")

# ============================================================ 04 BUFFER CONSUMERS
tsv4 = ["CONS_ID\tCONSUMER_TYPE\tRVA\tINSN\tRAW_BYTES\tREADS_FROM\tDATA_EXPR\tVALUE_USED_AS\tDESTINATION\tCONFIDENCE\tNOTE"]
rows4 = [
 ("C-001","header_parse","0x235F94",ins(0x235F94),bhex(0x235F94,7),
  "[ebp-0x10C] (recv buf base, offset 0)",
  "cl = buf[0] & 0x0F","IP IHL -> icmp_off = ihl*4","edx/ecx (index)","CONFIRMED_DATAFLOW",
  "buf[0] low nibble = IP header length/4; NOT an opcode"),
 ("C-002","header_parse","0x235FAD",ins(0x235FAD),bhex(0x235FAD,7),
  "[ebp+ecx-0x108] = buf + icmp_off + 4",
  "ebx = dword at ICMP id field","compared to obj+0x08 (GetCurrentProcessId)","comparison (jne 0x235FD5)","CONFIRMED_DATAFLOW",
  "ICMP identifier match; obj+0x08 written 0x235D6A"),
 ("C-003","header_parse","0x235FB4",ins(0x235FB4),bhex(0x235FB4,7),
  "[ebp+ecx-0x10C] = buf + icmp_off",
  "ecx = &ICMP header","base ptr for type/seq/timestamp reads","ecx","CONFIRMED_DATAFLOW",
  "icmp_off = (buf[0]&0xF)*4"),
 ("C-004","protocol_check","0x235FC0",ins(0x235FC0),bhex(0x235FC0,4),
  "[ecx] = ICMP[0]","cmp byte [ecx],0","ICMP type == 0 (echo reply) else reject","branch to 0x235FD5","CONFIRMED_DATAFLOW",
  "type 8 sent, 0 required on reply"),
 ("C-005","protocol_check","0x235FCB",ins(0x235FCB),bhex(0x235FCB,5),
  "[ecx+8] = ICMP[8]","cmp word [ecx+8], bx","ICMP sequence == expected seq","branch to 0x236058","CONFIRMED_DATAFLOW",
  "bx = [ebp-0x12c] = obj+0x12 seq"),
 ("C-006","rtt_extract","0x236058",ins(0x236058),bhex(0x236058,4),
  "[ecx+0xC] = ICMP[0xC]","eax = now_tick - [ecx+0xC]","round-trip time","out+0x04","CONFIRMED_DATAFLOW",
  "timestamp echoed from request at 0x235E9E"),
 ("C-007","ttl_extract","0x236061",ins(0x236061),bhex(0x236061,7),
  "[ebp-0x104] = buf + 8","ecx = movzx byte buf[8]","IP TTL of reply","out+0x0C","CONFIRMED_DATAFLOW",
  "IP header offset 8 = TTL"),
 ("C-008","length_derive","0x23606E",ins(0x23606E),bhex(0x23606E,5),
  "edi = recvfrom return","edi = edi - ihl*4 - 0x10","payload length","out+0x08","CONFIRMED_DATAFLOW",
  "no payload bytes copied"),
 ("C-009","write_out","0x236073",ins(0x236073),bhex(0x236073,3),
  "bx","mov word [out], bx","seq","out+0x00","CONFIRMED_DATAFLOW",""),
 ("C-010","no_copy","0x23607C",ins(0x23607C),bhex(0x23607C,4),
  "-","xor eax,eax ; return","function returns 0 without payload copy","-","CONFIRMED_DIRECT",
  "NEGATIVE EVIDENCE: no memcpy/rep movs of [ebp-0x10C]; buffer does not escape"),
]
for r in rows4:
    tsv4.append("\t".join(r))
tsv4.append("\t".join(("C-011","netevents","0x235F52",ins(0x235F52),bhex(0x235F52,5),
  "[ebp-0x170] (WSANETWORKEVENTS)","test byte [ebp-0x170],1","FD_READ readiness bit","branch","CONFIRMED_DIRECT",
  "event readiness only, not payload")))
tsv4.append("\t".join(("C-012","absent","-","-","-","-","-","-","-","CONFIRMED_ABSENT",
  "NEGATIVE EVIDENCE: no opcode/handler-table dispatch, no netchan, no persistent buffer, no decrypt/decompress on this path")))
W("04_BUFFER_CONSUMERS.tsv", "\n".join(tsv4) + "\n")

print("03 and 04 written")
