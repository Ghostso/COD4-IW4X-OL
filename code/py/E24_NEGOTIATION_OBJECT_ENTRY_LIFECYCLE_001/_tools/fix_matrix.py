from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
p=base/"E24_HANDSHAKE_OPCODE_DIRECTION_MATRIX.md"; t=p.read_text(encoding="utf-8")
old="""- **与协商对象关系**：无直接边。
- **与 HMAC/接收计数器**：两条 0x84 分支**都**调用 `0x6AAA770`（置连接状态 4），即该码在进入处理函数后**立即**触发失败态（`0x6AC269`/`0x6AC329`）。这一点是与其它码的显著差异。
- **等级**：控制流关联 **PROVEN**；语义（为何 0x84 直接失败）**BLOCKED**。"""
new="""- **与协商对象关系**：无直接边。
- **与 HMAC/接收计数器**：两条 0x84 分支在处理函数 `0x6A9690` **返回后**，分派器**无条件**调用 `0x6AAA770`（`0x6AC273`/`0x6AC333`），把连接状态 `[+0xC8]` 置 4（终止）；其后才用 `test bl,bl` 决定是否继续构造 `0x1C` 对象。这是与其它码的显著差异：0x84 与"会话终止"强相关。
- **等级**：控制流关联 **PROVEN**；"0x84 = 终止/关闭类消息" **INFERRED（强）**（依据：无条件转入 `0x6AAA770`，该函数唯一副作用链是 `[+0xC8]=4`）；具体协议命名 **BLOCKED**。"""
assert old in t
t=t.replace(old,new)
old2="| 0x84 | 未找到常量 | `0x6AC25B`/`0x6AC31B` -> `0x6A9690` | 无 | 无直接边 | 两分支均转 `0x6AAA770` | 控制流 PROVEN / 语义 BLOCKED |"
# find actual row
import re
for ln in t.splitlines():
    if ln.startswith("| 0x84 |"):
        old2=ln; break
new2="| 0x84 | 未找到常量 | `0x6AC25B`/`0x6AC31B` → `0x6A9690` | 无 | 无直接边 | 返回后无条件转 `0x6AAA770`（置 `[+0xC8]=4`） | 控制流 PROVEN / 终止语义 INFERRED(强) |"
t=t.replace(old2,new2)
p.write_text(t,encoding="utf-8")
print("updated matrix")
print([l for l in t.splitlines() if l.startswith("| 0x84 |")])
