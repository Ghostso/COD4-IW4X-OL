#!/usr/bin/env python3
"""把 MEMORY.md 压回 <17510: 精简 127/128、136、137, 不够再丢后备条目."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

REPL = {
 "- [★★★★★ 静态侧全清":
  "- [★★★★★ 静态侧全清+三处旧结论更正(137)](codol-static-full-clear-137.md) — ★★★**13 项静态项全收口 + 3 处旧结论更正**。"
  "①★★★**131 名字列整体错位一格**（根因=`as_family_scan` 在 `0x693DD0` 处取 `[f+8]`=**下一条记录的 COL**；真布局 `[COL][vf0][vf1]`、**步进 12**）"
  "⇒**`0x5D39E0`=`AS_UILog`**（**130 对、135 的「更正 130」作废**）、`0x5D3C80`=AS_SetRecommendedSetting、`0x5D3CB0`=**AS_SetVideoSetting**、`0x5D42C0`=**AS_GetServerTime**、`0x5D2E70`/`0x5D2F00`=AS_CreateRoom/AS_JoinRoom；"
  "**「UILog/QuickMatch/setdvar 同址 `0x8435E0`」作废**（共享者 22 个）。"
  "②★★**132 的「17 字节步进」作废**（间隙 **803/830=12**）。③★★**136 序号解码作废**（≤10=单十进制字符+`?`、≥11=hex 字母+`@`；**两形态=同一序号两种写法**；`?P@`=15）。"
  "④**B9** `sendGpuLatchedSettings`=**双表+哨兵桩(`0x8435D0`=`C3`)转发**，处理器 `0x77EB10`。⑤**B10** `configure_mp.csvNNN`=`\\x15` 前缀**诊断消息簇**。"
  "⑥**B12/B13** 头部不变量 **195/195**；`u16@[5:7]==4·(F1>>10)` ⇒ **「×4」不是量纲**。⑦**B14** 32768B、**96.55% 恒定**、u16 细胞间距 4。"
  "⑧**R1a** `playlist 37`=**num**。⑨**R2a** `UIClickCount`=`${TIMESTAMP}`（绝对）。⑩**R2b** `[esi+0x14]=3`=**相对时间戳槽位计数**（推翻 129）。⑪**R3** `932`=svc4 请求字段 #0（352 次全在偏移 1）。"
  "★边界：R1b 字段名不可得 / B11 页号不由 C++ 出 / V 语义·M 语义·`0x15` 语义·932 名未定。"
  "★方法论**两法互证才定位**、**步长用直方图**、**「结构对」+「名字对」≠「绑定对」**、**「无法定单位」先试「是别的字段的一部分」**",
 "- [★★★★★ AS面静态收口":
  "- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — ★★★纯静态收口。"
  "①**真注册器=825(精确)**：判据改**双向有界**(`[入口,首ret)` 内有短名 push)⇒828 里**恰 3 条非注册器**；★135 的「≤825」真因=我的 `cstr(maxlen=40)` 截断 4 个长名。"
  "②★★★**7 个 View 的 62 个 Flash 回调全表**(`._SF_Handler@?<n>@??Init@UiCpp<View>@@`)：UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4；★`AS_*`=Flash 调 C++、`On*Click`/`On*Change`=C++ 调 Flash。"
  "③★★★**三方互证 62=28+11+6+5+5+4+3** ⇒ View 注册站点=7 个分批函数。④`?<n>`=**`Init` 内全部局域类型声明序**（跨 View 重复⇒非全局）。"
  "⑤★★**`and eax,0x8F`=全局值类型判据**(2801 处)；★类型名「这里没有」(AS3 VM 类无 RTTI)。⑥10 个「非唯一调用者」=8 个跨容器注册+2 个非注册器。"
  "⑦**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI 名=`AS_<短名>`**；★★精确化 133/135：**ctor 写 `RefCountImplCore`+refcount、dtor shim 才写 `GFx::FunctionHandler`**。"
  "⑧`[0xc77bb98]` 创建点=`0x5EB9D0`→`manager->vt[0x60]`。"
  "★方法论**「未找到」先查自己的过滤器常数**、**判据两端都要有界**、**异质互证**、**用「重复值」否证「索引假设」**、**「未定」分「没找到/这里没有」**",
 "- [★★★★★ 遥测信封":
  "- [★★★★★ 遥测信封+宏引擎+三套${}命名空间(127/128)](codol-telemetry-envelope-and-macro-engine.md) — 54 模板无注册表(全摊平到调用点 `push imm32`)；统一信封 `0x9C7044` 含 **build `1649370`** 铁证；队列 1024 满静默丢；宏引擎 `0x640AB0`（只认 `${TIMESTAMP_PLACEHOLDER}`/`${CLIENT_IP_PLACEHOLDER}`，`/1000` ⇒ **单位秒**，改写成 `${TIMESTAMP_OFFSET(%d)}`）；**`${CODOID}/${ZONEID}` 客户端不解释** ⇒ 服务端 TLog 契约；三套 `${}` 实现互不相干；UIPage/UIClick 无模板（运行时 `'%d'` 拼）。★搜引用必区分**指针 vs push imm32**〔★137：`UIClickCount` 用**绝对**`${TIMESTAMP}`，经 `%s` 实参注入〕",
}

FALLBACK = ["- [★★ 大厅字节文法已100%闭合", "- [★★★ 根模式映射"]

lines = io.open(MEM, encoding="utf-8").read().split("\n")
lines = [next((t for p, t in REPL.items() if ln.startswith(p)), ln) for ln in lines]
dropped = []
for pref in FALLBACK:
    if len("\n".join(lines).encode("utf-8")) <= LIMIT:
        break
    before = len(lines)
    lines = [ln for ln in lines if not ln.startswith(pref)]
    if len(lines) < before:
        dropped.append(pref)
s = "\n".join(lines)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("新字节数 %d (limit %d)" % (len(s.encode("utf-8")), LIMIT))
print("后备丢弃:", dropped or "无")
