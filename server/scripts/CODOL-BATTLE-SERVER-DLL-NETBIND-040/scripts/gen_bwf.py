# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

# ---- BUFFER_WRITE_AND_LENGTH_FLOW.tsv
hdr=["EVID_ID","STAGE","INSN_RVA","INSN_VA","FILE_OFF","RAW_BYTES","SEMANTIC",
     "BUFFER_PTR","LENGTH_VALUE","RETURN_OR_STATUS","WRITES_TO","CONFIDENCE","NOTE"]
rows=[
 ("BWF-001","socket create","0x235D6D","0x10235D6D","0x23516D","ff15602ab010",
  "WSASocketW(af=2,type=3,proto=1,0,0,0)","-","-","EAX=SOCKET","obj[+0x00]","CONFIRMED_DIRECT","only WSASocketW site in DLL"),
 ("BWF-002","event create","0x235D4F","0x10235D4F","0x23514F","ff156c2ab010",
  "WSACreateEvent()","-","-","EAX=HANDLE","obj[+0x04]","CONFIRMED_DIRECT",""),
 ("BWF-003","event bind","0x235D81","0x10235D81","0x235181","ff15682ab010",
  "WSAEventSelect(s, hEvent, 1=FD_READ)","s","FD_READ","EAX","-","CONFIRMED_DIRECT",""),
 ("BWF-004","send request","0x235EC9","0x10235EC9","0x2352C9","ff154c2ab010",
  "sendto(s, obj[+0x0C], 0x30, 0, &from, 0x10)","obj[+0x0C]","0x30","EAX","-","CONFIRMED_DIRECT","ord 20; precedes wait"),
 ("BWF-005","event wait","0x235F23","0x10235F23","0x235323","ff15702ab010",
  "WSAWaitForMultipleEvents(1, &obj[+4], FALSE, 100, FALSE)","-","100ms","EAX(0xC0/0x102)","-","CONFIRMED_DIRECT","timeout handling 0x102/0xC0"),
 ("BWF-006","event decode","0x235F4C","0x10235F4C","0x23534C","ff15642ab010",
  "WSAEnumNetworkEvents(s, obj[+4], &netevents)","-","-","EAX","[ebp-0x170]","CONFIRMED_DIRECT","checks FD_READ bit 0x1"),
 ("BWF-007","RECV","0x235F7E","0x10235F7E","0x23537E","ff15482ab010",
  "recvfrom(s, [ebp-0x10C], 0x100, 0, &from, &fromlen)","[ebp-0x10C]","0x100","EAX=bytes","[ebp-0x10C]","CONFIRMED_DATAFLOW","ord17; the closed link"),
 ("BWF-008","len capture","0x235F84","0x10235F84","0x235384","8bf8",
  "mov edi,eax","-","EAX","EDI","-","CONFIRMED_DATAFLOW","recv length moved to EDI"),
 ("BWF-009","err check","0x235F86","0x10235F86","0x235386","83ffff",
  "cmp edi,-1","-","-1","ZF","-","CONFIRMED_DIRECT","SOCKET_ERROR branch"),
 ("BWF-010","type nibble","0x235F94","0x10235F94","0x235394","8a8df4feffff",
  "mov cl,[ebp-0x10C] ; and cl,0x0F","buf[0]","0x0F","CL","-","CONFIRMED_DATAFLOW","low nibble of first byte"),
 ("BWF-011","src/identity check","0x235FBB","0x10235FBB","0x2353BB","3b5e08",
  "cmp ebx,[obj+8] (pid)","buf ptr","-","ZF","-","CONFIRMED_DATAFLOW","compares against obj[+0x08]"),
 ("BWF-012","out length write","0x236058","0x10236058","0x235458","2b410c",
  "sub eax,[ecx+0x0C] ; mov [esi_out+4],eax","-","-","EAX","out[+0x04]","CONFIRMED_DATAFLOW","derived length"),
 ("BWF-013","payload len write","0x23606E","0x1023606E","0x23546E","2bf8",
  "sub edi,eax ; sub edi,0x10","EDI","0x10","EDI","out[+0x08]","CONFIRMED_DATAFLOW","truncates 0x10 hdr"),
 ("BWF-014","out word write","0x236073","0x10236073","0x235473","66891e",
  "mov word [esi_out],bx","-","BX","-","out[+0x00]","CONFIRMED_DATAFLOW","type/identity word"),
 ("BWF-015","out byte write","0x236079","0x10236079","0x235479","894e0c",
  "mov [esi_out+0x0C],ecx","-","-","ECX","out[+0x0C]","CONFIRMED_DATAFLOW","lparam/flags byte"),
 ("BWF-016","NEXT PARSE","","","","", "no netchan/opcode dispatch observed after 0x23607C","-","-","-","-","UNKNOWN","chain stops here"),
]
lines=["\t".join(hdr)+"\n"]
for r in rows: lines.append("\t".join(r)+"\n")
W("BUFFER_WRITE_AND_LENGTH_FLOW.tsv","".join(lines))
print("BUFFER rows:",len(rows))
