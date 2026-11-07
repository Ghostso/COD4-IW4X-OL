#!/usr/bin/env python3
"""138 定稿：更新 INDEX（替换 138 行 + 新增 47type/分发键行）与 MEMORY。"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IDX = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\INDEX.md"
MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

IDX_138 = (
 "| [138](papers/lobby/138_大厅战斗服全链路专项_dwRoom协议层彻底解开.md) | "
 "**大厅↔战斗服全链路专项 / dwRoom 协议层彻底解开** | "
 "★★★ **十二路静态 + 两次实机对照 + 活进程 dump。**"
 "①★★★**`[0x76446B0]`=`clientState`(CA_*)，开局闸门要求 `<3`** ⇒ **客户端连着服务器就拒绝本地开局**，开局必须服务端下发 `dwRoomMessageStartGame`；5 个写入点全定位。"
 "②★★★**`ready_push.on` 双推送共用 `seq=请求+1000` ⇒ `10054` RST**；删开关后 **0 断连且能进房间**。"
 "③★★★**两轮实机跑的都是旧版 GOLDEN(`D7EEB456`,1323 行)**，修复全在 **VERIFIED(`FF473204`,1575 行)**；**VERIFIED 跑过依然无效**。"
 "④★★★**房间事件不走 6/5 也不走 11/4 应答体**，走 **`dwRoom` 协议（独立一层，语料从未出现）**；实测 `11/4` blob 喂 `0x637000` 判据：ready 族首5位=3 但 3位=4、room 族首5位=0 ⇒ **全部走不通**。"
 "⑤★★★**分发键 = `0x1122334455667788`**（srpc 记录 `0xE374650` 的 +0x10/+0x14 = `0x55667788`/`0x11223344`），dwRoom 消息首个 u64 必须等于它否则丢弃。"
 "⑥★★★**Manifold 条目 64 位 = 归属者 ID**：`0`=广播放行、`=本机账号 ID 0xE7C8A98A6B4C2D0E`=定向、**其他值 ⇒ `0x637166` 摘链释放（静默丢弃）**。"
 "⑦**完整投递链**：`0xB838A0`→`0xB7B210`(opcode6)→`0x7F1060`(slot[6],vtable`0xDE07A4`)→`0x7E7C90`(按 u64 匹配)→`0x6371F0`(双 tag0x13 blob)→`0x637000`(read5==3+read8,==1→Manifold)→`0x6256C0`→归属过滤→`0x634870`(**47 项表 `0x636F3C`**)。"
 "⑧★★**47 种 dwRoomMessage 字段位宽全表**（跳转表 47/47 逐项复算 + 35 个构造器 `[obj+4]==type` 双向自证）；**字段码名表 `0xB773D0` 25 项实见**（0=NoType/1=Bool/3=UChar8/8=UInt32/0x10=String/0x13=Blob/0x15=FullType/…）。"
 "⑨★★`rec+0x90`(Ready)唯一写点=`0x635A86`(case 0x10)，本地点准备只发不写；`rec+0x88`(阵营)本地 `0x62A24C` 直写。"
 "⑩★★`+0x105FE`←dvar`\"3265\"`←playlist`rule 3265`；`dwRoomImp` 字段表全出（`+0x278`/`+0x105D8`/`+0xE368` 19×0x1D0/两数组各 **50**）。"
 "⑪★★**魔数 B `0x8D51E398`=`crc32(\"combat\")`**。⑫★★建房序 **13/13 次 `11/13` 先于 `21/1`**。"
 "★诚实边界：Manifold **语料 0 真实样本**（构造序列纯反汇编推导）/ dwRoom opcode↔srpc 无静态表 / `0x82E1458` 描述符表磁盘全 0 / `0x12`·`0x1D` 若干槽语义未定。"
 "★方法论**先验跑的版本(hash)**、**最便宜验证最先做**、**因果只能靠改一个变量**、**扫描寻址形态决定能找到什么**、**\"发了没反应\"先查路由键不是格式** | ★★★★★ |"
)

# 删除旧的 138 行（旧文件名）
OLD_PREFIX = "| [138](papers/lobby/138_大厅战斗服全链路专项_房间黑箱清零.md)"

lines = io.open(IDX, encoding="utf-8").read().split("\n")
out, placed = [], False
for ln in lines:
    if ln.startswith(OLD_PREFIX):
        out.append(IDX_138)
        placed = True
        continue
    out.append(ln)
if not placed:
    # 没找到旧行，插在 137 之后
    out2, done = [], False
    for ln in out:
        out2.append(ln)
        if not done and ln.startswith("| [137](papers/lobby/137_"):
            out2.append(IDX_138)
            done = True
    out = out2
    placed = done
io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("INDEX 138 行:", "已更新" if placed else "失败", "行数", len(lines), "->", len(out))

# ---- MEMORY：压缩 138 行 ----
MEMROW = (
 "- [★★★★★ 大厅↔战斗服全链路+dwRoom协议层(138)](codol-lobby-battle-handoff-138.md) — ★★★**房间黑箱清零**。"
 "①★★★**`[0x76446B0]`=`clientState`(CA_*)，开局闸门要求<3**⇒**连着服务器就拒绝本地开局**⇒必须服务端下发StartGame。"
 "②★★★**`ready_push.on`双推送共用`seq=请求+1000`⇒`10054`RST**；删开关后**0断连且能进房间**。"
 "③★★★**两轮实机跑的都是旧版GOLDEN(`D7EEB456`)**，修复全在**VERIFIED(`FF473204`)**；**VERIFIED 跑过依然无效**。"
 "④★★★**房间事件不走6/5也不走11/4**，走**dwRoom协议**（独立一层，语料从未出现；`11/4` blob 喂 `0x637000` 判据全失败）。"
 "⑤★★★**分发键=`0x1122334455667788`**（srpc记录`0xE374650` +0x10/+0x14），dwRoom 消息首个 u64 必须等于它。"
 "⑥★★★**Manifold 条目 64 位=归属者ID**：`0`=广播放行、`=账号ID 0xE7C8A98A6B4C2D0E`=定向、**其他⇒静默丢弃**。"
 "⑦**投递链**`0xB838A0`→`0xB7B210`→`0x7F1060`→`0x7E7C90`→`0x6371F0`→`0x637000`→`0x6256C0`→`0x634870`(**47项表`0x636F3C`**)。"
 "⑧★★**47 种 type 字段位宽全表**+**字段码名表`0xB773D0` 25 项实见**(0=NoType/1=Bool/3=UChar8/8=UInt32/0x10=String/0x13=Blob/0x15=FullType)。"
 "⑨★★`rec+0x90`(Ready)唯一写点`0x635A86`(case0x10)；`rec+0x88`(阵营)本地`0x62A24C`直写。"
 "⑩★★魔数B`0x8D51E398`=`crc32(\"combat\")`。⑪★★建房序 **11/13先于21/1(13/13)**。"
 "★方法论**先验跑的版本(hash)**、**最便宜验证最先做**、**因果只能靠改一个变量**、**扫描寻址形态决定能找到什么**、**\"发了没反应\"先查路由键**"
)

mlines = io.open(MEM, encoding="utf-8").read().split("\n")
out2 = []
for ln in mlines:
    if ln.startswith("- [★★★★★ 大厅↔战斗服全链路"):
        out2.append(MEMROW)
    else:
        out2.append(ln)
s = "\n".join(out2)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("MEMORY 新字节数", len(s.encode("utf-8")), "(limit %d)" % LIMIT)
