#!/usr/bin/env python3
"""把 136 行插到 INDEX.md 的 135 行**之后**(按行首锚定)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\INDEX.md"

ROW = (
    "| [136](papers/lobby/136_AS面静态收口_825注册器与62个Flash回调全表.md) | "
    "**AS 面静态收口 / 825 注册器（精确）/ 62 个 Flash 回调全表** | "
    "★★★ **纯静态收口卷（不依赖任何动态验证），闭掉 135 的 §边界 B1/B3/B4/B5/B6 + 部分 B2。**"
    "①★★**真注册器 = 825（精确，不再是下界）**：判据换成**双向有界**的"
    "「`[入口, 首条 ret)` 内存在 `push <可打印短名(≥3字符)>`」⇒ `as_regfns_v2.json` 的 828 里"
    "**恰好 3 条不是注册器**（`0x6A7650`/`0x6AEBD0`/`0x728350`）。★135 只敢说「≤825」的**真因是我的 `cstr(maxlen=40)`**："
    "7 个「无短名」里 4 个是**长名被截断**（最长 `AS_GetTimeInMillisecondsUntilNextBatchOfItemsExpire` 49 字符）。"
    "②★★**7 个 View 的 Flash 回调全表 = 62 个**（名字直接写在镜像：`._SF_Handler@?<n>@??Init@UiCpp<View>@@QAEXAAVValue@GFx@Scaleform@@@`）："
    "`UiCppView`3 / `MatchSelectView`28 / `ItemListView`11 / `Onboarding`6 / `SuggestedLoadoutView`5 / `ChallengesView`5 / `NewItems`4。"
    "★补齐 130/131 悬了四卷的 UI 面名字：**`AS_*` = Flash 调 C++（容器属性）；`On*Click`/`On*Change` = C++ 调 Flash（View 注册的接收器）——同一 Scaleform 面的两个方向**。"
    "③★★★**三方互证同一组数字**（62=28+11+6+5+5+4+3）：①RTTI 局域类名计数 ⊗②分批函数注册器计数（135）⊗③132 的 RTTI 计数"
    "⇒**View 注册站点 = 7 个分批函数，一 View 一个**；`0x7396F0`(3)=基类 `UiCppView` 三件套。★并顺手给 135 的弱证据（`0x748A70` 这个 VA）补了强旁证。"
    "④**序号收口**：`?<n>` = MSVC 局域类序号；**同一序号值跨 View 重复**（`?P@`=25 同时在 MatchSelectView 与 ItemListView）⇒ 非全局索引；"
    "且 MatchSelectView 序号**最大 337 而 handler 仅 28** ⇒ 序号索引的是「`Init` 内**全部局域类型**的声明序号」。⇒ **132 的「声明顺序」成立，但不能当 handler 序号用**。"
    "★序号在地址上**倒挂**（大了反而地址低）⇒ 不能用地址顺序推声明顺序。★两种 mangled 形态（`@?<n>??Init@` 与 `@?<n>@??Init@`）并存、`OnSortClick` 以 25/300 两序号各现一次，成因**未定案**。"
    "⑤★★**B3 收口（类型标签判据）**：`and eax,0x8F` 全镜像 **2801 处**，其后 `cmp al,imm8` 值域 = `{0x0A:2457, 0x09:9, 0x06:1, 0x05:1}` + `cmp eax,1` 分支 ⇒ **`(x & 0x8F)==常量` 是全局通用的值类型判据**（不是业务标志）。"
    "旁证：`mov [reg+0xC], imm32` 直方图（1088 处）主值恰为 **0..10 小枚举**（0×416/2×215/3×114/1×92/4×40/6×37/5×28/…/0x0A×4）⇒ `+0xC` 是小枚举字段。掩码 `0x8F=0x0F|0x80` ⇒ 低4位=类型、bit7=标志。"
    "★**类型名未定且可证「这里没有」**：按关键字穷举 RTTI（`Scaleform` 133/`GFx` 86）而 `Interpreter`/`Movie`/`Sprite`/`Loader`/`GFxPlayer`/`AVMP`/`ASVM` **全 0** ⇒ **AS3 VM 类没进 RTTI 表**。"
    "⑥**B5 收口**：10 个「非唯一调用者」 = **8 个注册器被 2–3 个分批函数调用**（= 同一 handler 注册到**多个容器**，如 `AS_IsInClan` ×3）+ 2 个已确认非注册器 ⇒ 非假条目，且解释 133 的「同名多对象」。"
    "⑦★★**注册器身份机械闭环**：`mov [eax],<vtable>` → `vtable[-1]`(COL) → `type_info`(**名字在 `ti+8`**) → **RTTI 名 = `AS_<短名>`**；逐例验证 `AS_JoinRoom`/`AS_IsInClan`/`AS_ShowShoutcastAndUpdateBypassMouseInput`/`AS_TryToUpdatePrimaryWeaponCountToPartyMember`/`AS_GetTimeInMillisecondsUntilNextBatchOfItemsExpire`。"
    "★★并**精确化 133/135**：ctor 第一写 `0xDC7AF4` = **`Scaleform::RefCountImplCore`**（引用计数基类）、`[+4]=1` = **refcount=1**；写 `Scaleform::GFx::FunctionHandler`（`0xDC7BA4`）的是**析构 shim**（`0x693DD0`）⇒ **ctor 写 RefCountImplCore，dtor 写 FunctionHandler**（两卷把两者混称「父类 vptr」）。"
    "★这给 133 的 `as_name_to_vtable.json` 一条**完全独立的交叉验证路径**（结构侧 vs 字符串侧）。"
    "⑧**B4 收口**：`[0xc77bb98]` **创建点** = `0x5EB9D0`（一次性，门=`[0xc7ae9a0]`/`[0xc77bb98]` 双零）→ `0x823ba0` 造 manager → **`[0xc77bb98] = 0x4F70A0(manager) = manager->vt[0x60](&ctx(0x2000,-1…,size=0x10),0,0)`**，随后在其上调 `vt[0x38]/[0x40]/[0x60]/[0x68]/[0x84]`；**销毁点** = `0x5ED804`/`0x5EDA5F`（清零 + `0x830BE0` 析构）。"
    "★`GFx::Value`(32位本 build) = **20 字节**（`+0xC`=类型/标志、`+0x10`=附加；`0x730690` 里那格是**类名字符串指针**，类型写 6 ⇒ 旁证「类型 6=字符串」）；`GFx::Value::ObjectInterface` RTTI 存在（`0xE730F0`）⇒ 注册器的 `[[edi+8]]->vt[0x14]` 是**对象接口方法槽**（槽名未定）。"
    "★ 边界 6 条已列（含「825 的前提 = 828 是 134 的产物」）。★ 方法论：**「未找到」先查自己的过滤器常数**、**判据两端都要有界才能给精确值**、**异质互证才算互证**、**用「重复值」否证「索引假设」**、**「未定」要分「没找到」与「这里没有」**、**vtable 反查类名把模糊词变精确** | ★★★★★ |"
)

src = io.open(P, encoding="utf-8").read().split("\n")
out = []
done = False
for ln in src:
    out.append(ln)
    if not done and ln.startswith("| [135](papers/lobby/135_"):
        out.append(ROW)
        done = True
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("插入成功" if done else "未找到 135 行!")
print("行数 %d %d" % (len(src), len(out)))
