#!/usr/bin/env python3
"""138 卷：往 INDEX.md 插 138 行（在 137 行之后）+ 往 MEMORY.md 插 138 行并压到限额内。"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IDX = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\INDEX.md"
MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

IDXROW = (
 "| [138](papers/lobby/138_大厅战斗服全链路专项_房间黑箱清零.md) | "
 "**大厅↔战斗服全链路专项 / 房间黑箱清零** | "
 "★★★ **五路并行静态 + 两次实机对照实验 + 活进程 dump。**"
 "①★★★**房间消息不走 `6/5` 也不走 `11/4` 应答体**，走 **`dwRoom` 协议 opcode=6**（两路独立互证：`0xB841D0` 与 `0x6371F0` 无调用关系；`0x17/0x1A` 超 6/5 的 0x15 上界）。"
 "②★★★**完整投递链打通到消息泵**：`0xB838A0`(handleMessage)→`0xB7B210`(opcode6)→`0x7F1060`(dwLobbyEventHandler slot[6], vtable `0xDE07A4`)→`0x7E7C90`(遍历 0x25D0 槽表,按 u64 ID 匹配)→`call [slot+0x25B8]`=`0x6371F0`(双 `tag0x13` blob)→`0x637000`(`lea edx,[len*8]`+`0xB779A0` 建位流)→`0xB774E0` 读3位tag/`0xB772E0` 读8位type→`0x634870`(**47项表 `0x636F3C`**,type 0..0x2E)。"
 "③★★★**服务端应写的格式**：两个 `tag 0x13 + u32 len + data` blob，内层位流 `3位tag(3)+8位type+字段`；Ready(0x10)=`code3+8位`+`code1+1位`、RoomStateUpdated(0x17)=`+code0x15+32位状态+code0x15+32位float`、ChangeTeam(0x14)/Vote(0x1A)=`+code0x15+32位值`、StartGame(0x03)=3个blob。★客户端读侧**断言 tag 相等**⇒必须逐位对齐。"
 "④★★★**`[0x76446B0]`=`clientState`(CA_* 枚举)**，开局闸门要求 **<3**(=DISCONNECTED/CINEMATIC/LOGO)⇒**客户端连着服务器就拒绝本地开局**⇒开局必须服务端下发 `StartGame`。5 个写入点全定位(`0x470469`=3/`0x5BE90A`=7/`0x5BEA8B`=4/`0x77C343`=0/`0x813D34`=7)；CA_* 字符串表 `0xDC0900`。"
 "⑤★★★**`ready_push.on` 双推送共用 `seq=请求seq+1000` ⇒ 客户端 `10054` RST**；对照实验删该开关后 **0 断连且能进房间**（GOLDEN L1196 缺陷；VERIFIED L1477 `_pseq=out_seq` 已修）。"
 "⑥★★★**两轮实机跑的都是旧版 GOLDEN(`D7EEB456`,1323行)**，全部修复在 **VERIFIED(`FF473204`,1575行)**⇒**修复从未被执行**。"
 "⑦★★**`rec+0x90`(Ready)唯一写点=`0x635A86`(case 0x10)**，本地点准备只发不写⇒不回 Ready 永不显示已准备；**`rec+0x88`(阵营)由本地 `0x62A24C` 直写**⇒按钮立即变灰(解释症状不对称)。"
 "⑧★★**`+0x105FE`(人数上限)←dvar `\"3265\"`(0x1C2B064)←playlist `rule 3265`(2×vsrule)**；`dwRoomImp` 字段表全出(`+0x278` 建立/`+0x105D8` 成员数/`+0xE368` 19×0x1D0 成员表/`+0x340`+`+0x7470` 各 **50**×0x238)。"
 "⑨★★**魔数 B `0x8D51E398`=`crc32(\"combat\")`**(实测；`crc32(\"sd\")/\"coop\"/\"playlist\"` 均在语料对上)⇒更正 112 卷。⑩★★**建房顺序 13/13 次 `11/13` 先于 `21/1`**⇒服务端顺序反了。"
 "★诚实边界：opcode6↔srpc(svc,task) 绑定未定 / 槽表算术 2 槽 vs 声明 20 待核 / 两 blob 分工未定 / `0x45B` 状态码未定名 / 47项表多数 handler 语义未定。"
 "★方法论**症状矛盾⇒找被挡住**、**用户的\"不对称\"=代码两条路径**、**因果只能靠改一个变量**、**★★实验前必须 hash+报版本**、**判据反直觉⇒查值域语义** | ★★★★★ |"
)

MEMROW = (
 "- [★★★★★ 大厅↔战斗服全链路专项(138)](codol-lobby-battle-handoff-138.md) — ★★★**房间黑箱清零**。"
 "①★★★**房间事件不走 6/5 也不走 11/4 应答体**，走 **dwRoom opcode=6**(两路互证)。"
 "②★★★**投递链**：`0xB838A0`(handleMessage)→`0xB7B210`(opcode6)→`0x7F1060`(dwLobbyEventHandler slot[6],vtable`0xDE07A4`)→`0x7E7C90`(遍历0x25D0槽表按u64 ID匹配)→`call[slot+0x25B8]`=`0x6371F0`(双tag0x13 blob)→`0x637000`(`lea edx,[len*8]`)→`0x634870`(**47项表`0x636F3C`**)。"
 "③★★★**服务端格式**=两个`tag13+u32len+data` blob，内层`3位tag(3)+8位type+字段`；Ready(0x10)/RoomStateUpdated(0x17)/ChangeTeam(0x14)/Vote(0x1A)/StartGame(0x03)序列化器全解；★客户端**断言tag相等**必须逐位对齐。"
 "④★★★**`[0x76446B0]`=`clientState`(CA_*枚举)，开局闸门要求<3**(DISCONNECTED/CINEMATIC/LOGO)⇒**连着服务器就拒绝本地开局**⇒必须服务端下发StartGame。5写入点全定位，CA_*表`0xDC0900`。"
 "⑤★★★**`ready_push.on`双推送共用`seq=请求+1000`⇒`10054`RST**；删开关后**0断连且能进房间**(GOLDEN L1196 缺陷/VERIFIED L1477 已修)。"
 "⑥★★★**两轮实机跑的都是旧版GOLDEN(`D7EEB456`1323行)**，修复全在**VERIFIED(`FF473204`1575行)**⇒**修复从未执行**。"
 "⑦★★`rec+0x90`(Ready)唯一写点`0x635A86`(case0x10)，本地点准备只发不写⇒不回Ready永不显示；`rec+0x88`(阵营)本地`0x62A24C`直写⇒按钮即灰。"
 "⑧★★`+0x105FE`←dvar`\"3265\"`←playlist`rule 3265`；`dwRoomImp`字段表全出(`+0x278`/`+0x105D8`/`+0xE368`19×0x1D0/两数组各**50**)。⑨★★**魔数B`0x8D51E398`=`crc32(\"combat\")`**。⑩★★建房序 **13/13 次 11/13 先于 21/1**⇒服务端反序。"
 "★方法论**症状矛盾⇒找被挡住**、**用户的\"不对称\"=代码两条路径**、**因果只能靠改一个变量**、**★★实验前必须hash+报版本**、**判据反直觉⇒查值域语义**"
)

# ---- INDEX ----
lines = io.open(IDX, encoding="utf-8").read().split("\n")
out, done = [], False
for ln in lines:
    out.append(ln)
    if not done and ln.startswith("| [137](papers/lobby/137_"):
        out.append(IDXROW)
        done = True
io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("INDEX 插入:", done, " 行数", len(lines), "->", len(out))

# ---- MEMORY ----
mlines = io.open(MEM, encoding="utf-8").read().split("\n")
out2, done2 = [], False
for ln in mlines:
    out2.append(ln)
    if not done2 and ln.startswith("- [★★★★★ 静态侧全清"):
        out2.append(MEMROW)
        done2 = True
s = "\n".join(out2)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("MEMORY 插入:", done2, " 新字节数", len(s.encode("utf-8")), "(limit %d)" % LIMIT)
