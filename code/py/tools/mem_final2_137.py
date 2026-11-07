#!/usr/bin/env python3
"""第二轮压缩: 把 135/136/137 三条改短, 目标 <17510."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MEM = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

L137 = ("- [★★★★★ 静态侧全清+三处旧结论更正(137)](codol-static-full-clear-137.md) — ★★★**13 项静态项全收口+3 处旧结论更正**。"
 "①**131 名字列错位一格**(`as_family_scan` 在 `0x693DD0` 处取 `[f+8]`=下一条记录的 COL；真布局 `[COL][vf0][vf1]`、**步进 12**)"
 "⇒**`0x5D39E0`=`AS_UILog`**(**130 对、135 的「更正 130」作废**)、`0x5D3CB0`=AS_SetVideoSetting、`0x5D42C0`=AS_GetServerTime；共享 `0x8435E0` 的 22 个名字换。"
 "②**132「17 字节步进」作废**(间隙 **803/830=12**)。③**136 序号解码作废**(≤10=单十进制字符+`?`、≥11=hex 字母+`@`；**两形态=两种写法**)。"
 "④**B9** 双命令表+哨兵桩(`0x8435D0`=`C3`)转发、处理器 `0x77EB10`。⑤**B10** `configure_mp.csvNNN`=`\\x15` 诊断消息簇。"
 "⑥**B12/B13** 不变量 195/195、`u16@[5:7]==4·(F1>>10)` ⇒ **「×4」不是量纲**。⑦**B14** 32768B/96.55% 恒定/u16 细胞间距 4。"
 "⑧**R1a** `playlist 37`=num。⑨**R2a** `UIClickCount`=绝对 `${TIMESTAMP}`。⑩**R2b** `[esi+0x14]=3`=**相对时间戳槽位计数**(推翻 129)。⑪**R3** `932`=svc4 字段#0。"
 "★边界：R1b 字段名不可得 / B11 页号非 C++ 常量 / V·M·`0x15` 语义未定。"
 "★方法论**两法互证才定位**、**步长用直方图**、**「结构对」+「名字对」≠「绑定对」**")

L136 = ("- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — ★★★纯静态。"
 "①**真注册器=825(精确)**(828 里恰 3 条非注册器；★135 的「≤825」真因=我的 `cstr(maxlen=40)` 截断 4 个长名)。"
 "②★★★**7 个 View 的 62 个 Flash 回调全表**(UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4)；`AS_*`=Flash 调 C++、`On*Click/Change`=C++ 调 Flash。"
 "③★★★**三方互证 62=28+11+6+5+5+4+3** ⇒ View 注册站点=7 个分批函数。④`?<n>`=**`Init` 内全部局域类型声明序**。"
 "⑤**`and eax,0x8F`=全局值类型判据**(2801 处)；类型名「这里没有」。⑥**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI 名=`AS_<短名>`**；**ctor 写 `RefCountImplCore`+refcount、dtor shim 才写 `GFx::FunctionHandler`**。"
 "⑦`[0xc77bb98]` 创建点 `0x5EB9D0`。★方法论**「未找到」先查自己的过滤器常数**、**判据两端须有界**、**异质互证**")

L135 = ("- [★★★★★ AS注册链三层归属+GFx转发器表(135)](codol-as-registration-3layer-135.md) — ★★★机制层收口+更正 134 两条。"
 "①**三层**：`0x5ED010`(一次性 AS 初始化，载 `scaleform/default/codo.gfx`)→3 容器主函数(`0x5EBB00`/`0x5EBB90`/`0x5EBDD0`)→分批函数(44 个 E8)→828 单名注册器；`[0xc77bb98]`=Scaleform 全局单例。"
 "②★★**3 个 AS3 容器类名**(各 1 引用)：`codo.common.CFunctionCommonContainer`/`CFunctionContainer`/`CFunctionInGameContainer`@`0xDC418C/41B4/41D4`。"
 "③★★**名字→对象映射的肯定式答案**：容器=`0x730690` 里 `0x830B00(global,\"flash.utils.getDefinitionByName\")` **反射取到的 AS3 类对象**，注册器往它身上**定义属性** ⇒ **表在 SWF/AS3 运行时**。"
 "④注册器模板 `[[edi+8]]->vt[0x14]([edi+0x10],\"JoinRoom\",&Value16,bool((容器.flags&0x8F)==0x0A))`。"
 "⑤★★**GFx 转发器 thunk 表** `0x830AC0..0x830BC0` 9 个 17 字节，slot∈`{0xB0..0xC8,0xE4,0xE8}` ⇒ 闭掉 133/134 连抄两卷的「0x830BC0 容器语义未解」。⑥分批函数序言 `57 8b f8 56`。"
 "⑦**更正 134 §⑤**：`0x6AEBD0`=分批函数、`0x728350`=惰性初始化，**都不是注册器**(真因=窗口向下跨函数)。★方法论**判据窗口须双向设防**、**同形字节模板=族指纹**、**「未解」会传染**〔★137：本卷「更正 130」作废(131 名字错位)〕")

lines = io.open(MEM, encoding="utf-8").read().split("\n")
rep = {"- [★★★★★ 静态侧全清": L137,
       "- [★★★★★ AS面静态收口": L136,
       "- [★★★★★ AS注册链三层归属": L135}
lines = [next((t for p, t in rep.items() if ln.startswith(p)), ln) for ln in lines]
s = "\n".join(lines)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(s)
print("新字节数 %d (limit %d)" % (len(s.encode("utf-8")), LIMIT))
