# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
ROOT=C.ROOT
def bhex(rva,n):
    d=raw(rva,n); return d.hex() if d else ""
def ins(rva):
    i=dis_at(rva); return "%s %s"%(i.mnemonic,i.op_str) if i else "?"
L=["FIELD_ID\tOFFSET\tSIZE\tFIELD_NAME\tSEMANTIC\tWRITE_RVA\tWRITE_INSN\tRAW_BYTES\tSOURCE_EXPR\tSOURCE_ORIGIN\tREADER\tREADER_RVA\tCONFIDENCE\tNOTE"]
L.append("\t".join(("OUT-000","+0x00","2","seq","ICMP reply sequence (echoed)",
 "0x236073",ins(0x236073),bhex(0x236073,3),"bx (=inc [D+0x12], request seq)",
 "request seq counter D+0x12 (0x235E9A)",
 "no direct reader found in thread proc 0x231050; downstream consumer UNKNOWN","-",
 "CONFIRMED_DATAFLOW","word write; = ICMP field buf[ihl*4+8]")))
L.append("\t".join(("OUT-004","+0x04","4","rtt","round-trip time",
 "0x236068",ins(0x236068),bhex(0x236068,4),"eax = tick(0x236110) - [ecx+0xC]",
 "now minus echoed timestamp buf[ihl*4+0xC] (written 0x235E9E)",
 "no direct reader found in thread proc 0x231050; downstream consumer UNKNOWN","-",
 "CONFIRMED_DATAFLOW","echoed tick set at 0x235E9E")))
L.append("\t".join(("OUT-008","+0x08","4","payload_len","recvlen - ihl*4 - 0x10",
 "0x236076",ins(0x236076),bhex(0x236076,3),"edi = recvlen - ihl*4 - 0x10",
 "recvfrom return EDI + IP IHL",
 "no direct reader found in thread proc 0x231050; downstream consumer UNKNOWN","-",
 "CONFIRMED_DATAFLOW","fixed 0x10 overhead; NO payload bytes copied")))
L.append("\t".join(("OUT-00C","+0x0C","4","ttl","reply IP TTL (zero-extended byte)",
 "0x236079",ins(0x236079),bhex(0x236079,3),"ecx = movzx byte [ebp-0x104] (= buf[8])",
 "IP header TTL byte of raw packet",
 "thread proc 0x231050 reads [esp+0x20] = out+0x0C","0x231171",
 "CONFIRMED_DATAFLOW","IP TTL of ICMP echo reply; value stored into job+4 at 0x231179")))
L.append("\t".join(("OUT-FRAME","(frame)","-","caller stack",
 "out base = [esp+0x14] (16B); D object = [esp+0x24] (= out+0x10)",
 "0x23107C","lea esi,[esp+0x24] ; call 0x235CD0",bhex(0x23107C,7),"-",
 "`out` is thread-proc stack; passed by pointer to 0x235E00 via 0x2310DA/0x2310DE",
 "0x231112 / 0x231129","0x231112","CONFIRMED_DIRECT",
 "D+0x00 socket freed 0x23111C; D+0x04 event freed 0x23112E")))
io.open(os.path.join(ROOT,"03_OUT_STRUCTURE_FIELDS.tsv"),"w",encoding="utf-8",newline="").write("\n".join(L)+"\n")
print("\n".join(L))
