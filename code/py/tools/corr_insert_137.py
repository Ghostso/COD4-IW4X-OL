#!/usr/bin/env python3
"""在 131/132/135/136 四卷的标题行后插入 137 的更正标注.
注意: 本文件字符串内**不用**半角双引号(用「」)，避免把 Python 字符串截断."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\papers\lobby"

M = {
 "131_AS原生函数登记表定名UserComplaint与sendGpuLatchedSettings.md":
  "> ★★ **137 卷更正（重要）**：本卷 §四 的**名字列整体错位一格**（`as_family_scan` 在 `0x693DD0` 处取 `[f+8]` = **下一条记录**的 COL；真布局是 `[COL][vf0=0x693DD0][vf1=handler]`、步进 **12**）。修正后的名字↔处理器表见 137 §1.1；受影响定名：`0x5D39E0`=**AS_UILog**、`0x5D3C80`=**AS_SetRecommendedSetting**、`0x5D3CA0`=AS_SetTierSetting、`0x5D3CB0`=**AS_SetVideoSetting**、`0x5D3DA0`=AS_IIPS_Response、`0x5D42C0`=**AS_GetServerTime**、`0x5D09C0`=AS_GetPlayListIdForNum、`0x5D0A10`=AS_GetPlayListNumForId、`0x5D0A60`=AS_IsDMZGametype、`0x5D2E70`=AS_CreateRoom、`0x5D2F00`=AS_JoinRoom。另：`configure_mp.csv652..663` 不是「键表」，是 `\\x15` 前缀的**诊断消息簇**（137 §5）。",
 "132_AS对象虚表结构定案与829对象族谱.md":
  "> ★★ **137 卷更正**：本卷「**真实步进 17 字节**」「131 按 12 ⇒ 每 4 个对象错位一格」**作废** —— 实测 `0x693DD0` 字面量相邻间隙 **803/830 = 12**，`0xDC8910`/`0xDC8988` 直读亦确认 `[COL][vf0][vf1]` **12 字节紧排**。本卷其余结论（COL 判据 / 829 对象 / `0x693DD0` = 共享标量删除析构 shim / Flash 经 `vtable[1]` 间接调用 / 63 个 `?N@??Init@UiCppXxx@@` 局域类）**不受影响**；137 §3 已独立复核 `0xDC7BA4`=2 槽、`0xDC7AF4`=1 槽、AS_* 各 2 槽。",
 "135_AS注册链三层归属与GFx转发器表.md":
  "> ★★ **137 卷更正（三条）**：①「**更正 130：`0x5D39E0`=`AS_SetRecommendedSetting`**」**作废** —— 真名是 **`AS_UILog`**，因此 **130 卷「`0x1D39E0` 是 UI 事件派发器」是对的**；②`0x5D3CB0` 的真名是 **`AS_SetVideoSetting`**（不是 `AS_IIPS_Response`）；③「`AS_UILog`/`AS_QuickMatch`/`AS_setdvar` 三者同址 `0x8435E0` 空实现」**作废** —— 共享 `0x8435E0` 的 22 个对象名单见 137 §1.1（**`AS_UILog` 不在其中**，它是真实现）。根因：131 的名字列错位一格（137 §1.1）。",
 "136_AS面静态收口_825注册器与62个Flash回调全表.md":
  "> ★★ **137 卷更正**：①本卷 §4/§0-4 的**序号数值作废**（base-26 解出的 21/23/25/297…/337 全错）。正确规则 = **值 ≤10 用单个十进制字符 + 终止符 `?`；值 ≥11 用十六进制字母 `A`..`P`（A=0..P=15）+ 终止符 `@`** ⇒ `?P@`=15、`?L@`=11、`?BB@`=17、`?BD@`=19、`?CB@`=33、`?CP@`=47（137 §2）。**两种 mangled 形态 = 同一序号的两种写法**（不是两种作用域）；本卷 §2 里「`OnSortClick` 以 25/300 两序号各现一次」应改为**两个都是形 B**（15 与 20）。②本卷 §0-2 引用的「`AS_UILog`/`AS_QuickMatch`/`AS_setdvar` = `c2 04 00` 空实现」**作废**（131 名字错位所致，见 137 §1.1）。③本卷 §0-7 的 `AS_JoinRoom` vtable `0xDC8910` 与 `AS_*` 名映射**仍然成立**（137 §3 两法互证）。",
}

for fn, mark in M.items():
    p = BASE + "\\" + fn
    try:
        lines = io.open(p, encoding="utf-8").read().split("\n")
    except FileNotFoundError:
        print("缺文件:", fn)
        continue
    out = [lines[0], "", mark] + lines[1:]
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("已插入:", fn)
