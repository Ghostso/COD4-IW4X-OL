#!/usr/bin/env python3
"""137 卷: 往 INDEX.md 插 137 行(在 136 行之后) + 往 MEMORY.md 插 137 行
并把 132/133/134/census 四条压短, 保持 MEMORY < 17510."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IDX = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\INDEX.md"
MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

IDXROW = (
 "| [137](papers/lobby/137_静态侧全清卷_13项收口与三处旧结论更正.md) | "
 "**静态侧全清 / 13 项收口 / 三处旧结论更正** | "
 "★★★ **纯静态（不启动客户端、不抓包、不读活进程）。** "
 "★★★**三处旧结论更正**：①**131 的名字列整体错位一格**（根因：`as_family_scan` 在 `0x693DD0` 处取 `[f+8]` = **下一条记录**的 COL；真布局 `[COL][vf0=0x693DD0][vf1=handler]`、**步进 12**）"
 "⇒ `0x5D39E0`=**`AS_UILog`**（**故 130 的「UI 事件派发器」是对的、135 的「更正 130」作废**）、`0x5D3C80`=AS_SetRecommendedSetting、`0x5D3CA0`=AS_SetTierSetting、`0x5D3CB0`=**AS_SetVideoSetting**、`0x5D3DA0`=AS_IIPS_Response、`0x5D42C0`=**AS_GetServerTime**、`0x5D09C0`/`0x5D0A10`=AS_GetPlayListIdForNum/NumForId、`0x5D2E70`/`0x5D2F00`=AS_CreateRoom/AS_JoinRoom；**「`UILog`/`QuickMatch`/`setdvar` 同址 `0x8435E0`」作废**（共享者 22 个，名单见卷）。"
 "②**132 的「17 字节步进」作废**：`0x693DD0` 间隙 **803/830 = 12**。③**136 的序号解码作废**：值≤10=单十进制字符+`?`、≥11=hex 字母 A..P+`@` ⇒ `?P@`=15、`?CP@`=47，**两形态=同一序号的两种写法**。"
 "**13 项状态**：✅闭合 = B7/B8/B9/B10/B12(结构层)/B13/B14(段图层)/R1a/R2a/R2b/R3；⚠️边界 = R1b(字段名不可得)/B11(页号不由 C++ 出)。"
 "★要点：**B9** `sendGpuLatchedSettings` **双表注册 + 哨兵桩(`0x8435D0`=`C3`)二级派发**，处理器 `0x77EB10`=`push 1; call 0x77E600`；**B10** `configure_mp.csvNNN` = `\\x15` 前缀**诊断消息簇**（652 排最后）；"
 "**B12/B13** 头部 8 项不变量 **195/195**、`u16@[5:7] == 4·(F1>>10)`（**「×4」不是量纲**）、V=02 `F1>>10==len-10` **112/112**；**B14** 解压 32768B、**96.55% 恒定**、u16 细胞间距 4、`0x27xx`/`0xeaXX` 双族（更正 `[12,3862)` 恒定但非全 0）；"
 "**R1a** `playlist 37`=**num**；**R2a** `UIClickCount` = `${TIMESTAMP}` 经 `%s` 实参注入（绝对，闭 129）；**R2b** `[esi+0x14]=3` = **相对时间戳槽位计数**（**推翻 129 猜测**，`0x640100` 唯一写点）；**R3** `932` = **svc4 请求字段 #0**（352 次全在 payload 偏移 1）。"
 "★余额度：V 语义 / K(V≠02) 式 / M 语义 / 尾文法 / `0x15` 语义 / 932 语义名 / 8/3 ID 族名。"
 "★方法论：**两法互证才能定「位」**、**步长一律用直方图**、**「结构对」+「名字对」≠「绑定对」**、**「两类」先试「同一东西的两种写法」**、**「无法定单位」先试「是别的字段的一部分」** | ★★★★★ |"
)

LEAN = {
 "- [★★★★★ AS注册链全闭合":
   "- [★★★★★ AS注册链全闭合+816短名全表+AS_DMZ(133)](codol-as-registration-chain-133.md) — ★★★**「名字→对象表」根本不存在**：每接口一个 0xB9 字节注册器，体内 `mov [eax],<vtable>`+`push <短名>`+`call [edx+0x14]` 三者焊死；**816 短名↔829 对象已导表** `tools/as_name_to_vtable.json`；62 个 `?N@` 局域类同路径；★★**`AS_DMZ_*` 整簇 9 个⇒撤离模式 UI 齐备**⇒修正「PvE 整体不完整」。★方法论**「找不到 X」先问 X 该不该存在**、**找注册器用行为指纹**、**「找到 N 个」必配「多少无归属」**〔★136/137 修正：真注册器 = **825**；名字表以 137 §1.1 为准〕",
 "- [★★★★★ AS注册器逐字节重验":
   "- [★★★★★ AS注册器逐字节重验(134)](codol-as-registrar-reverify-134.md) — ★★**133 的 838 = 828 真 + 10 假**；判据 `cc cc` + 体内 `mov [reg],<vtable>` + vtable∈829 + 距入口 ≤0x400 ⇒ 828 候选，唯一未覆盖 = `FunctionHandler` 抽象父类（永不注册）；★★**「9 个双注册」整条作废**；★★★**`UiCppMainMenu` 定身份**：`.?AVUiCpp*` RTTI **只 1 个** ⇒ 7 个 View 全是**无虚表普通类**、`::Init` 无符号；62 局域类分布 MatchSelectView28/ItemListView11/…/**MainMenu 零条**；`codo.cpp.UiCppXxx` = `__FILE__`；**UiCppMainMenu = 只监听不暴露接口**；**`AS_MainMenuWillReload`(0x68EC20) = 主菜单刷新钩子**；★★自我推翻 3 条 ⇒ **算术差≠集合差**、**写完工具前不许写数字**〔★137：真注册器 = **825**〕",
 "- [★★★★★ 单字节角色分账":
   "- [★★★★★ 单字节角色分账+报文方向(0x00..0xFF)](codol-byte-role-census-00-70.md) — 0x00/01/07/08/0a/10/6b/6c/70/FF 逐角色分账（详见各单字节卷）；三核心 ID（账号 `0xE7C8A98A6B4C2D0E` / 频道**魔数 C** `0x1122334455667788` 三路径 / 账号低 32 位 `0x6B4C2D0E`）；**魔数 A `0xD692ADAB` = matchmaking query criterion 且 build 派生**、**魔数 B `0x8D51E398` = 描述符尾**；**6848 条 100% 客户端→服务端**；**请求侧已无字节黑箱**；剩余黑箱 = 应答侧 + 未触发服务（需授权跑客户端）；★黑箱先查旧卷 / i32·u32 双读 / 新魔数先算术枚举 / 字符串 ID 去客户端找名字池",
}

# ---- INDEX ----
lines = io.open(IDX, encoding="utf-8").read().split("\n")
out, done = [], False
for ln in lines:
    out.append(ln)
    if not done and ln.startswith("| [136](papers/lobby/136_"):
        out.append(IDXROW)
        done = True
io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("INDEX 插入:", done, " 行数", len(lines), "->", len(out))

# ---- MEMORY ----
NEW137 = (
 "- [★★★★★ 静态侧全清+三处旧结论更正(137)](codol-static-full-clear-137.md) — ★★★**13 项静态项全收口 + 3 处旧结论更正**。"
 "①★★★**131 名字列整体错位一格**（根因：`as_family_scan` 在 `0x693DD0` 处取 `[f+8]` = **下一条记录的 COL**；真布局 `[COL][vf0][vf1]`、**步进 12**）"
 "⇒ `0x5D39E0`=**`AS_UILog`**（**130 的「UI 事件派发器」是对的、135 的「更正 130」作废**）、`0x5D3C80`=AS_SetRecommendedSetting、`0x5D3CB0`=**AS_SetVideoSetting**、`0x5D42C0`=**AS_GetServerTime**、`0x5D2E70`/`0x5D2F00`=AS_CreateRoom/AS_JoinRoom；**「UILog/QuickMatch/setdvar 同址 0x8435E0」作废**（共享者 22 个）。"
 "②★★**132 的「17 字节步进」作废**：间隙 **803/830 = 12**。③★★**136 序号解码作废**：值≤10=单十进制字符+`?`、≥11=hex 字母+`@` ⇒ `?P@`=15、`?CP@`=47，**两形态=同一序号两种写法**。"
 "④**B9** 闭合：`sendGpuLatchedSettings` **双表注册**（主表哨兵桩 `0x8435D0`=`C3` / 次表 `0x331D408`；`0x4F2D70` 建链、`0x4F2C40` 派发）+ 处理器 `0x77EB10`。"
 "⑤**B10** 闭合：`configure_mp.csvNNN` = `\\x15` 前缀**诊断消息簇**（652 排最后；652/653/656/661 为无 `%` 无参标记）。"
 "⑥**B12/B13**：头部 8 项不变量 **195/195**；**`u16@[5:7]==4·(F1>>10)` ⇒「×4」不是量纲**；V=02 `F1>>10==len-10` **112/112**。"
 "⑦**B14**：解压 32768B、**96.55% 恒定**、u16 细胞间距 4、`0x27xx`/`0xeaXX` 双族（★更正 `[12,3862)` 恒定但非全 0）。"
 "⑧**R1a**：`playlist 37`=**num**。⑨**R2a**：`UIClickCount` = `${TIMESTAMP}` 经 `%s` 实参注入（绝对）。"
 "⑩**R2b**：`[esi+0x14]=3` = **相对时间戳槽位计数**（推翻 129；`0x640100` 唯一写点）。⑪**R3**：`932` = svc4 请求字段 #0（352 次全在偏移 1）。"
 "★边界：R1b 字段名不可得、B11 页号不由 C++ 出、V 语义/K 式/M 语义/`0x15` 语义/932 名未定。"
 "★方法论**两法互证才能定「位」**、**步长一律用直方图**、**「结构对」+「名字对」≠「绑定对」**、**「两类」先试「同一东西两种写法」**、**「无法定单位」先试「是别的字段的一部分」**"
)

mlines = io.open(MEM, encoding="utf-8").read().split("\n")
out2, done2 = [], False
for ln in mlines:
    for pref, txt in LEAN.items():
        if ln.startswith(pref):
            ln = txt
            break
    out2.append(ln)
    if not done2 and ln.startswith("- [★★★★★ AS面静态收口"):
        out2.append(NEW137)
        done2 = True
s = "\n".join(out2)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("MEMORY 插入137:", done2, " 新字节数", len(s.encode("utf-8")), "(limit %d)" % LIMIT)
