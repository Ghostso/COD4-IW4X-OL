#!/usr/bin/env python3
"""138: 再把 138 行压短 (~1900B -> ~1200B)，目标 <17510。"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

NEW = (
 "- [★★★★★ 大厅↔战斗服全链路专项(138)](codol-lobby-battle-handoff-138.md) — ★★★**房间黑箱清零**。"
 "①★★★**房间事件不走 6/5 也不走 11/4 应答体**，走 **dwRoom opcode=6**。"
 "②★★★**投递链**：`0xB838A0`(handleMessage)→`0xB7B210`(opcode6)→`0x7F1060`(dwLobbyEventHandler slot[6],vtable`0xDE07A4`)→`0x7E7C90`(遍历0x25D0槽表按u64 ID匹配)→`call[slot+0x25B8]`=`0x6371F0`(双tag0x13 blob)→`0x637000`→`0x634870`(**47项表`0x636F3C`**)。"
 "③★★★**服务端格式**=两个`tag13+u32len+data` blob，内层`3位tag(3)+8位type+字段`；Ready(0x10)/RoomStateUpdated(0x17)/ChangeTeam(0x14)/Vote(0x1A)/StartGame(0x03) 序列化器全解；★客户端**断言tag相等**必须逐位对齐。"
 "④★★★**`[0x76446B0]`=`clientState`(CA_*)，开局闸门要求<3**⇒**连着服务器就拒绝本地开局**⇒必须服务端下发StartGame。"
 "⑤★★★**`ready_push.on`双推送共用`seq=请求+1000`⇒`10054`RST**；删开关后**0断连且能进房间**。"
 "⑥★★★**两轮实机跑的都是旧版GOLDEN(`D7EEB456`)**，修复全在**VERIFIED(`FF473204`)**⇒**修复从未执行**。"
 "⑦★★`rec+0x90`(Ready)唯一写点`0x635A86`(case0x10)⇒不回Ready永不显示；`rec+0x88`(阵营)本地`0x62A24C`直写⇒按钮即灰。"
 "⑧★★`+0x105FE`←dvar`\"3265\"`←playlist`rule 3265`；`dwRoomImp`字段表全出。⑨★★**魔数B`0x8D51E398`=`crc32(\"combat\")`**。⑩★★建房序 **13/13 次 11/13 先于 21/1**⇒服务端反序。"
 "★方法论**症状矛盾⇒找被挡住**、**因果只能靠改一个变量**、**★★实验前必须hash+报版本**、**判据反直觉⇒查值域语义**"
)

lines = io.open(MEM, encoding="utf-8").read().split("\n")
lines = [NEW if ln.startswith("- [★★★★★ 大厅↔战斗服全链路专项") else ln for ln in lines]
s = "\n".join(lines)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("新字节数 %d (limit %d)" % (len(s.encode("utf-8")), LIMIT))
