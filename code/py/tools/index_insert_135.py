#!/usr/bin/env python3
"""把 135 行插到 INDEX.md 的 134 行之前(按行首锚定, 不依赖整行匹配)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\INDEX.md"

ROW = (
    "| [135](papers/lobby/135_AS注册链三层归属与GFx转发器表.md) | "
    "**AS 注册链三层归属 / GFx 转发器表 / 更正 134 两条** | "
    "★★★ **机制层收口 + 对 134 的实质性更正。**"
    "①**三层归属闭合**：`0x5ED010`（一次性 AS 初始化，门=`[0xc7ae9a0]!=0 || [0xc77bb98]!=0`，"
    "载 `scaleform/default/codo.gfx`）→ **3 个容器主函数** `0x5EBB00`/`0x5EBB90`/`0x5EBDD0` "
    "→ **分批函数**（`0x5EBB90` 体内 44 个不同 `E8` 目标）→ **828 单名注册器**。"
    "②★★ **三个 AS3 容器类名**（字符串池 `0xDC418C/41B4/41D4`，全镜像**各恰好 1 引用**）："
    "`codo.common.CFunctionCommonContainer`/`CFunctionContainer`/`CFunctionInGameContainer`，"
    "三处 `mov edi,imm32` 分别在 `0x5EBB12`/`0x5EBB9E`/`0x5EBDDE`。"
    "③★★ **名字→对象映射的肯定式答案**：容器是 `0x730690` 里用 "
    "`0x830B00(global,\"flash.utils.getDefinitionByName\"(0xDD6098),this,&Value,1)` "
    "**反射取到的 AS3 类对象**，注册器再往它身上定义属性——**表在 SWF/AS3 运行时里，C++ 侧只有动作**"
    "（133“表不存在”从否定式升为机制级解释）。"
    "④★★ **注册器逐字节**：`[[edi+8]]->vt[0x14]([edi+0x10],\"JoinRoom\"(&0xDC2730),&Value16,"
    "bool(([edi+0xc]&0x8F)==0x0A))`，`edi=&容器`、`esi=全局单例`；"
    "`0x830BC0` 产物非法时被 `test al,0x8f/je` 整段跳过。"
    "⑤★★ **GFx 转发器 thunk 表** `0x830AC0..0x830BC0` **9 个 17 字节同形 thunk**"
    "（`mov ecx,[ecx+0xC]; mov eax,[ecx]; mov eax,[eax+slot]; jmp eax`），"
    "slot ∈ `{0xB0..0xC8,0xE4,0xE8}` ⇒ **133/134 抄了两卷的“`0x830BC0` 容器语义未解”当场闭合**"
    "（`0x830BC0`=slot 0xC0，`0x830B00`=slot 0xE4）。"
    "⑥**分批函数统一序言** `57 8b f8 56` + N 组 `push esi; call <注册器>; add esp,4`。"
    "⑦归属汇总：`0x5EBB90`→347 / `0x5EBB00`→217 / `0x5EBDD0`→94 / "
    "**`0x748A70`→28（第二注册站点=按 View 注册）** / `0x5ED010`→25 / `0x748970`→11 / …；"
    "**0x5CEB10 的 133 观测“220 次”= 217 注册器 + 3 非注册器**。"
    "⑧**28 三路独立复现**（132 RTTI 局域类 ⊗ 133 调用次数 ⊗ 135 注册器归属）。"
    "⑨★★ **更正 134 §⑤**：`0x6AEBD0` 是**分批函数**（0xEE 字节、26 组 `push esi; call`、"
    "尾 `pop edi;ret`）、`0x728350` 是**惰性初始化**（0x2D 字节、无 vtable 写）——**两者都不是注册器**；"
    "真因是 134 的“体内前 0x300 字节”窗口**向下跨进了下一个函数**（134 只在“向上”方向设了防）。"
    "⇒ **真注册器 ≤825**。"
    "⑩`0xdae091`（130 空串哨兵）在 `0x5ED034` 有语义正常的调用点（dvar `tencent_e3_loadout` 默认值）"
    "⇒ 130 判据被独立复现。"
    "⑪AS 短名连续块 `0xDC26C0..0xDC2820` 与 131 表逐项吻合。"
    "★ 诚实边界：`0x0A`(掩码 0x8F) 语义未定 / 各 slot 的 GFx 方法名未定 / 分批函数数三口径=15/27/44（含嵌套）。"
    "★ 方法论：**判据窗口必须双向设防**、**“找不到表”的答案常是“表在另一台运行时里”**、"
    "**一个假条目会连锁制造假解释**、**同形字节模板=族指纹**、**数量差异先问口径**、"
    "**假阴性也要防火墙**、**“未解”会传染** | ★★★★★ |"
)

src = io.open(P, encoding="utf-8").read().split("\n")
out = []
done = False
for ln in src:
    if not done and ln.startswith("| [134](papers/lobby/134_"):
        out.append(ROW)
        done = True
    out.append(ln)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("插入成功" if done else "未找到 134 行!")
print("行数 %d %d" % (len(src), len(out)))
