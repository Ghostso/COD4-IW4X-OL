#!/usr/bin/env python3
"""第五轮: 精简 136 行 + 丢弃 1 条, 收口到 <17.1KB."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

L136 = (
    "- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — "
    "★★★纯静态收口(不依赖动态验证)。①**真注册器=825(精确)**：判据改用**双向有界**的"
    "「`[入口, 首ret)` 内有短名 `push`」⇒828 里**恰好 3 条非注册器**；"
    "★135 的「≤825」真因=我的 `cstr(maxlen=40)` 截断了 4 个长名(最长 49 字符)。"
    "②★★★**7 个 View 的 62 个 Flash 回调全表**(`._SF_Handler@?<n>@??Init@UiCpp<View>@@`)："
    "UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4；"
    "★`AS_*`=Flash 调 C++、`On*Click`/`On*Change`=C++ 调 Flash(**同一 Scaleform 面两个方向**)；补齐 130/131 悬了四卷的 UI 面名字。"
    "③★★★**三方互证 62=28+11+6+5+5+4+3**(RTTI 名 ⊗ 分批函数注册器数 ⊗ 132 计数)⇒**View 注册站点=7 个分批函数**(基类三件套 `0x7396F0`)。"
    "④`?<n>`=**`Init` 内全部局域类型的声明序**(同一序号跨 View 重复⇒非全局索引；最大 337 而 handler 仅 28)；★序号在地址上**倒挂**。"
    "⑤★★**`and eax,0x8F`=全局值类型判据**(2801 处，值域 `{0xA:2457,9,6,5,1}`)；★类型名「这里没有」(AS3 VM 类无 RTTI：Interpreter/Movie/Sprite/Loader/GFxPlayer/AVMP/ASVM 全 0)。"
    "⑥10 个「非唯一调用者」=8 个**跨容器注册**(如 `AS_IsInClan`×3)+2 个非注册器。"
    "⑦★★**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI 名=`AS_<短名>`**；"
    "★★精确化 133/135：ctor 写 `Scaleform::RefCountImplCore`+`[+4]=1`=**refcount**、**dtor shim 才写 `GFx::FunctionHandler`**(两卷混称「父类 vptr」) ⇒ "
    "`as_name_to_vtable.json` 获**结构侧独立交叉验证**。"
    "⑧`[0xc77bb98]` 创建点=`0x5EB9D0`→`manager->vt[0x60]`(`0x4F70A0`)、销毁=`0x5ED804`；`GFx::Value`=20 字节。"
    "★方法论**「未找到」先查自己的过滤器常数**、**判据两端都要有界才能给精确值**、**异质互证才算互证**、"
    "**用「重复值」否证「索引假设」**、**「未定」要分「没找到」与「这里没有」**、**vtable 反查类名把模糊词变精确**"
)

DROP = ["- [★ 外部方案已结项"]

lines = io.open(P, encoding="utf-8").read().split("\n")
out, n136, nd = [], 0, 0
for ln in lines:
    if ln.startswith("- [★★★★★ AS面静态收口"):
        out.append(L136)
        n136 += 1
        continue
    if any(ln.startswith(d) for d in DROP):
        nd += 1
        continue
    out.append(ln)
s = "\n".join(out)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("136 行替换 %d ; 丢弃 %d ; 新字节数 %d" % (n136, nd, len(s.encode("utf-8"))))
