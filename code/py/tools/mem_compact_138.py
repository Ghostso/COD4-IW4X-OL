#!/usr/bin/env python3
"""138: 压缩 MEMORY 到 <17510。把 131/133/134/136/137 五条压短(细节已在各自 topic 文件)。"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

REPL = {
 "- [★★★★★ 静态侧全清":
  "- [★★★★★ 静态侧全清+三处更正(137)](codol-static-full-clear-137.md) — ★★★**13 项全收口+3 处更正**。"
  "①**131 名字列错位一格**(`as_family_scan` 在 `0x693DD0` 处取 `[f+8]`=下一条记录的 COL；真布局 `[COL][vf0][vf1]`、**步进 12**)⇒**`0x5D39E0`=`AS_UILog`**(**130 对、135 的「更正 130」作废**)、`0x5D3CB0`=AS_SetVideoSetting、`0x5D42C0`=AS_GetServerTime。"
  "②**132「17 字节步进」作废**(间隙 **803/830=12**)。③**136 序号解码作废**(≤10=单十进制字符+`?`、≥11=hex 字母+`@`)。"
  "④**B9** 双命令表+哨兵桩(`0x8435D0`=`C3`)。⑤**B10** `configure_mp.csvNNN`=`\\x15` 诊断消息簇。"
  "⑥**B12/B13** 不变量 195/195、`u16@[5:7]==4·(F1>>10)` ⇒ **「×4」不是量纲**。⑦**B14** 32768B/96.55% 恒定。"
  "⑧**R1a** `playlist 37`=num。⑨**R2a** `UIClickCount`=绝对 `${TIMESTAMP}`。⑩**R2b** `[esi+0x14]=3`=相对时间戳槽位计数。⑪**R3** `932`=svc4 字段#0。",
 "- [★★★★★ AS面静态收口":
  "- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — ★★★纯静态。"
  "①**真注册器=825(精确)**(828 里恰 3 条非注册器；★135 的「≤825」真因=`cstr(maxlen=40)` 截断 4 个长名)。"
  "②★★★**7 个 View 的 62 个 Flash 回调全表**(UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4)；`AS_*`=Flash 调 C++、`On*Click/Change`=C++ 调 Flash。"
  "③★★★**三方互证 62=28+11+6+5+5+4+3** ⇒ View 注册站点=7 个分批函数。④`?<n>`=**`Init` 内全部局域类型声明序**。"
  "⑤**`and eax,0x8F`=全局值类型判据**(2801 处)。⑥**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI 名=`AS_<短名>`**；**ctor 写 `RefCountImplCore`+refcount、dtor shim 才写 `GFx::FunctionHandler`**。"
  "★方法论**「未找到」先查自己的过滤器常数**、**判据两端须有界**、**异质互证**",
 "- [★★★★★ AS注册器逐字节重验":
  "- [★★★★★ AS注册器逐字节重验(134)](codol-as-registrar-reverify-134.md) — ★★**133 的 838 = 828 真 + 10 假**；判据 `cc cc`+`mov [reg],<vtable>`+vtable∈829+距入口≤0x400 ⇒ 828 候选，唯一未覆盖 = `FunctionHandler` 抽象父类；★★**「9 个双注册」作废**；★★★**`UiCppMainMenu` 定身份**：`.?AVUiCpp*` RTTI **只 1 个** ⇒ 7 个 View 全是**无虚表普通类**、`::Init` 无符号；**MainMenu = 只监听不暴露接口**；**`AS_MainMenuWillReload`(0x68EC20) = 主菜单刷新钩子**〔★137：真注册器 = **825**〕",
 "- [★★★★★ AS注册链全闭合":
  "- [★★★★★ AS注册链全闭合+816短名全表+AS_DMZ(133)](codol-as-registration-chain-133.md) — ★★★**「名字→对象表」不存在**：每接口一个 0xB9 字节注册器，体内 `mov [eax],<vtable>`+`push <短名>`+`call [edx+0x14]` 三者焊死；**816 短名↔829 对象已导表**；★★**`AS_DMZ_*` 整簇 9 个⇒撤离模式 UI 齐备**⇒修正「PvE 整体不完整」〔★136/137：真注册器 = **825**〕",
 "- [★★★★★ AS_原生接口族定名":
  "- [★★★★★ AS_原生接口族定名(131)](codol-as-native-family-131.md) — 806 条 `[0x693DD0][handler][typeinfo]` 行定名(**RTTI 名在宿主+8**)；`0x5D3790`=`AS_TencentReportBadLanguage`/`UserComplaint`(`|`CR→`;`+500 上限)；★方法论**反汇编起点须 `int3` 锚定**、**0 调用点先问该不该有 call 边**、**起名需命名证据**〔★137：名字列整体错位一格，以 137 §1.1 为准〕",
}

FALLBACK = ["- [★★★ 剧情模式内容系统性缺损", "- [★ dvar表内存读法"]

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
