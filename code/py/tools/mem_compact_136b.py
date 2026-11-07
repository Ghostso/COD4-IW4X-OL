#!/usr/bin/env python3
"""第二轮压缩 MEMORY.md: 127/128、129、134、131、census 五条."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

NEW = {
    "- [★★★★★ 遥测信封":
        "- [★★★★★ 遥测信封+宏引擎+三套${}命名空间(127/128)](codol-telemetry-envelope-and-macro-engine.md) — 54模板无注册表(全摊平到调用点`push imm32`)；统一信封`0x9C7044`含**build `1649370`**铁证；队列`[0xc911f60]`1024满静默丢；宏引擎`0x640AB0`(`/1000`⇒**单位秒**)；**`${CODOID}/${ZONEID}`客户端不解释**⇒服务端TLog契约；**三套`${}`实现互不相干**(遥测`0x640AB0`/腾讯配置`0xB6A70`,`0xB6D10`/TLog消息`0xA567xx`)；★搜引用必区分**指针 vs push imm32**(自我撤回「第二遍引擎」)；UIPage/UIClick无模板(运行时`'%d'`拼格式)",
    "- [★★★★★ 遥测四入口":
        "- [★★★★★ 遥测四入口+65日志点全表(129)](codol-telemetry-four-entries-65-sites.md) — 入口**4个**：`0x640190`(7)/`0x6404B0`(56)/`0x640FD0`(2)/`0x63FC60`(7)；**65点/49事件**全表；ClientLoadout=**运行时循环拼接**(非模板,127问错了)；8条孤儿模板全走D入口(「NUL模板普查×调用点普查」双向差集发现)；D入口剥`\n`/`\r`⇒124的多行只能来自多条目拼接；**`ClientException`记完即`mov [0xe5735b],0`关总开关**；build编译日期`1649370 May  8 2021 21:20:01`；缺口：UIClickCount时间口径、A入口`[esi+0x14]=3`",
    "- [★★★★★ AS注册器逐字节重验":
        "- [★★★★★ AS注册器逐字节重验(134)](codol-as-registrar-reverify-134.md) — ★★**133的838=828真+10假**(集合差:仅133版那10个)；10假=`0x693DD0`(dtor)+2数据旁+**7个`00 00 eb 11`同模板内联中段**；判据`cc cc`+体内`mov [reg],<vtable>`+vtable∈829+距入口≤0x400⇒828候选,唯一未覆盖=`FunctionHandler`抽象父类(槽1`0xC3E8A6`纯虚,永不注册)；★★**「9个双注册」整条作废**；★★**2个「漏覆盖」是过滤器bug**〔★135更正:那两个根本不是注册器〕；★★★**UiCppMainMenu定身份**:`.?AVUiCpp*`RTTI**只1个**⇒7个View全是**无虚表普通类**,`::Init`无符号；62局域类分布 MatchSelectView28/ItemListView11/…/**MainMenu零条**；`codo.cpp.UiCppXxx`=`__FILE__`非类名表；**UiCppMainMenu=只监听不暴露接口**；**`AS_MainMenuWillReload`(0x68EC20)=主菜单刷新钩子**；★★本卷自我推翻3条⇒**算术差≠集合差**、**相关数字须一起做一致性检查**、**写完工具前不许写数字**",
    "- [★★★★★ AS_原生接口族定名":
        "- [★★★★★ AS_原生接口族定名(131)](codol-as-native-family-131.md) — 806条`[0x693DD0][handler][typeinfo]`行定名(**RTTI名在宿主+8**)；★**更正130：`0x5D39E0`=`AS_SetRecommendedSetting`**；`0x5D3790`=`AS_TencentReportBadLanguage`/事件`UserComplaint`(`|`CR→`;`+500上限)；`AS_UILog`/`AS_QuickMatch`/`AS_setdvar`=`c2 04 00`**空实现**；`AS_IIPS_Response`=`Cbuf_AddText`**非遥测**；`AS_SetTierSetting`写`configure_mp.csv`+dvar`1146`；★方法论**反汇编起点须`int3`锚定**、**0调用点先问该不该有call边**、**起名必须有命名证据**",
    "- [★★★★★ 单字节角色分账":
        "- [★★★★★ 单字节角色分账+报文方向(0x00..0xFF)](codol-byte-role-census-00-70.md) — 0x00/01/07/08/0a/10/6b/6c/70/FF 逐角色分账(详见各单字节卷)；三核心ID(账号`0xE7C8A98A6B4C2D0E`/频道**魔数C**`0x1122334455667788`三路径/账号低32位`0x6B4C2D0E`)；**魔数A `0xD692ADAB`=matchmaking query criterion且build派生**、**魔数B `0x8D51E398`=描述符尾固定字段**；**6848条100%客户端→服务端**；**请求侧已无字节黑箱**；剩余黑箱=应答侧+未触发服务(均需授权跑客户端)；★黑箱先查旧卷/i32·u32双读/新魔数先算术枚举/字符串ID去客户端找名字池",
}

lines = io.open(P, encoding="utf-8").read().split("\n")
repl = 0
for i, ln in enumerate(lines):
    for pref, txt in NEW.items():
        if ln.startswith(pref):
            lines[i] = txt
            repl += 1
            break
out = "\n".join(lines)
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("替换 %d 条 ; 新字节数 %d" % (repl, len(out.encode("utf-8"))))
