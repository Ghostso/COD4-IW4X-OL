#!/usr/bin/env python3
"""第六轮: 精简 136 行; 若仍 >17510 则按后备清单继续丢, 直到达标."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
LIMIT = 17510

L136 = (
    "- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — "
    "★★★纯静态收口。①**真注册器=825(精确)**：判据改**双向有界**(`[入口,首ret)`内有短名 push)⇒828 里**恰 3 条非注册器**；"
    "★135 的「≤825」真因=我的 `cstr(maxlen=40)` 截断了 4 个长名。"
    "②★★★**7 个 View 的 62 个 Flash 回调全表**(UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4)"
    "⇒★`AS_*`=Flash 调 C++、`On*Click`/`On*Change`=C++ 调 Flash(同一 Scaleform 面两方向)。"
    "③★★★**三方互证 62=28+11+6+5+5+4+3**⇒**View 注册站点=7 个分批函数**。"
    "④`?<n>`=**`Init` 内全部局域类型声明序**(跨 View 重复⇒非全局；最大 337 而 handler 仅 28)。"
    "⑤★★**`and eax,0x8F`=全局值类型判据**(2801 处，值域 `{0xA:2457,9,6,5,1}`)；★类型名「这里没有」(AS3 VM 类无 RTTI)。"
    "⑥**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI 名=`AS_<短名>`**；"
    "★★精确化 133/135：**ctor 写 `Scaleform::RefCountImplCore`+refcount、dtor shim 才写 `GFx::FunctionHandler`**。"
    "⑦`[0xc77bb98]` 创建点=`0x5EB9D0`→`manager->vt[0x60]`(`0x4F70A0`)。"
    "★方法论**「未找到」先查自己的过滤器常数**、**判据两端都要有界**、**异质互证**、**用「重复值」否证「索引假设」**、**「未定」分「没找到/这里没有」**"
)

FALLBACK = [
    "- [★★★★ 45个消息类型号",
    "- [★★★★ P2PInfo 与对等玩家槽",
    "- [★★★★ 房间逆向收口",
    "- [★ 出生点",
    "- [★★★ 剧情模式内容系统性缺损",
]

lines = io.open(P, encoding="utf-8").read().split("\n")
lines = [L136 if ln.startswith("- [★★★★★ AS面静态收口") else ln for ln in lines]

dropped = []
for pref in FALLBACK:
    if len("\n".join(lines).encode("utf-8")) <= LIMIT:
        break
    before = len(lines)
    lines = [ln for ln in lines if not ln.startswith(pref)]
    if len(lines) < before:
        dropped.append(pref)

s = "\n".join(lines)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("新字节数 %d (limit %d)" % (len(s.encode("utf-8")), LIMIT))
print("后备丢弃:", dropped or "无")
