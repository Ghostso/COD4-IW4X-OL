# -*- coding: utf-8 -*-
import os, json, hashlib, re
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = os.path.join(ROOT, "CODOL-DEMONWARE-BUNDLE-001")
d = json.load(open(os.path.join(OUT,"_register_raw.json"), encoding="utf-8"))
rows, tot, sc = d["rows"], d["total"], d["score"]
i4w, i4s = d["i4_weight"], d["i4_score"]

def esc(s): return (s or "").replace("|","\\|").replace("\n"," ").strip()

L=[]
A=L.append
A("# CODOL Demonware 统一问题登记簿（Q-01 … Q-111）")
A("")
A("> **口径（继承 E-15 §1 权重标度，未改动）**：I4=8 / I3=5 / I2=3 / I1=1；")
A("> 解决度：PROVEN=1.0、INFERRED(强)=0.6、INFERRED(弱)=0.3、BLOCKED=0.0、REFUTED=0.0、CLOSED=1.0。")
A("> **来源**：Q-01…Q-43 取 XVAL-02 权威账本 `XVAL02_QUESTION_REGISTER_MIGRATION.csv`；")
A("> Q-44…Q-111 取 E-21…E-27 与本项目两份登记簿增量的实测行。")
A("> **时点**：CLIENT-DEMONWARE-CODEC-KEYFLOW-001 交付后。")
A("")
A("## 1. 总账")
A("")
A("| 项 | 值 |")
A("|---|---:|")
A("| 问题总数 | %d |" % len(rows))
A("| 总权重（分母） | **%d** |" % tot)
A("| 加权得分 | **%.1f** |" % sc)
A("| 风险加权解决率（认知完备率） | **%.2f%%** |" % (100*sc/tot))
A("| I4 条目数 | %d |" % sum(1 for r in rows if r['impact']=='I4'))
A("| I4 权重 | **%d** |" % i4w)
A("| I4 加权得分 | **%.1f** |" % i4s)
A("| I4 加权完备率 | **%.2f%%** |" % (100*i4s/i4w))
A("| 实时互操作状态 | **NOT-OBSERVED** |")
A("")
A("**纪律**：认知完备率 ≠ 互通完成率。本表所有条目均保留其历史状态，");
A("被后续轮次推翻者以 `REFUTED` 记录并保留原文，不删除、不改权。")
A("")

# group by task
A("## 2. 全量条目")
A("")
A("| Q | 轮次 | 协议层 | 问题 | 影响 | 权重 | 状态 | 解决度 | 加权 | 证据引用 |")
A("|---|---|---|---|---|---:|---|---:|---:|---|")
for r in rows:
    A("| %s | %s | %s | %s | %s | %d | %s | %.1f | %.1f | %s |" % (
        r["q"], esc(r["task"]) or "-", esc(r["layer"]) or "-", esc(r["question"]),
        r["impact"], r["weight"], esc(r["status"]), r["score"], r["weighted"],
        esc(r["evidence"]) or "-"))
A("")

A("## 3. 分轮次增量与历史变更记录")
A("")
A("| 轮次 | 新增 Q | 权重增量 | 得分增量 | 交付时点总权重 | 交付时点得分 | 交付时点完备率 | 备注 |")
A("|---|---|---:|---:|---:|---:|---:|---|")
inc = [
 ("E-15 (基线)",      "Q-01…Q-16",  91,  32.0,  91,  32.0,  "35.17%", "权重标度首次定义"),
 ("XVAL-02 (权威账本)","Q-01…Q-43", 115, 56.9,  206, 88.9,  "43.16%", "登记簿口径校正：I4 分母 104；Q-14/Q-23/Q-26/Q-31/Q-33/Q-37 重评"),
 ("E-21",             "Q-44",        8,   0.0,  214, 88.9,  "41.54%", "REFUTED: E-21 前对 0xA85AD0 的段区判定"),
 ("E-22",             "Q-45",        5,   0.0,  219, 88.9,  "40.59%", "REFUTED: 五地址属 .data BSS（Q-48 后续推翻）"),
 ("E-23",             "Q-46…Q-48",  18,   9.8,  237, 98.7,  "41.65%", "更正常数 I4 分母 104→112；Q-48 REFUTED"),
 ("E-24",             "Q-49…Q-56",  47,  28.8,  284,127.5,  "44.89%", "Q-54 REFUTED（0x6AB310 有唯一调用者）"),
 ("E-25",             "Q-57…Q-67",  65,  42.0,  349,169.5,  "48.57%", "Q-65 REFUTED（三码不同队列）"),
 ("E-26",             "Q-68…Q-79",  76,  32.0,  425,201.5,  "47.41%", "Q-71 REFUTED（服务端无 CLIENTCHAL/BDDATA）"),
 ("E-27",             "Q-80…Q-91",  74,  32.0,  499,233.5,  "46.79%", "Q-81/Q-82/Q-86/Q-91 REFUTED；对端在生态外"),
 ("PEER-REUSE-AUDIT-001","Q-92…Q-102",71, 61.0, 570,294.5,  "51.67%", "REUSE-PARTIAL；Q-101 REFUTED（对端无 codec）"),
 ("CODEC-KEYFLOW-001","Q-103…Q-111",64,  56.0,  634,350.5,  "55.28%", "KEYFLOW-EQUIVALENT；更正上述两处措辞；Q-109 REFUTED、Q-111 BLOCKED"),
]
for a,b,c,e,f,g,h,i in inc:
    A("| %s | %s | +%d | +%.1f | %d | %.1f | %s | %s |" % (a,b,c,e,f,g,h,i))
A("")
A("**逐项复算（可对账）**：总权重 = %d；加权得分 = %.1f；完备率 = %.1f/%d = **%.3f%%**；" % (tot,sc,sc,tot,100*sc/tot))
A("I4 权重 = %d；I4 得分 = %.1f；I4 完备率 = %.1f/%d = **%.3f%%**。" % (i4w,i4s,i4s,i4w,100*i4s/i4w))
A("")
A("## 4. 历史变更记录（REFUTED / 重评 / 修正常数）")
A("")
A("| 变更 | Q | 原主张 | 变更后 | 依据轮次 |")
A("|---|---|---|---|---|")
hist = [
 ("重评", "Q-14", "传输/TLS 游戏协议", "CLOSED_NON_GAME", "XVAL-01/XVAL-02"),
 ("重评", "Q-23/Q-26/Q-31", "按原状态", "REGRADED(XVAL-01)", "XVAL-01"),
 ("重评", "Q-33/Q-37", "按原状态", "REGRADED(XVAL-02)", "XVAL-02"),
 ("重评", "Q-19/Q-15/Q-22", "按原状态", "CLOSED / MERGED", "XVAL-02"),
 ("REFUTED", "Q-48", "五下游地址属 .data BSS 虚拟尾部", "按 VA 归属 .text（354 直接调用点）", "E-23"),
 ("REFUTED", "Q-54", "0x6AB310 无直接调用", "唯一调用者 0x6AC192", "E-24"),
 ("REFUTED", "Q-65", "0x83/0x84/0x85 经同一应答队列", "三码各走独立处理函数", "E-25"),
 ("REFUTED", "Q-71", "服务端存在 CLIENTCHAL/BDDATA（codol_dedrun.exe 范围）", "该模块内无（范围 = codol_dedrun.exe）", "E-26"),
 ("REFUTED", "Q-81/Q-82", "2697 服务端生态含 Demonware 组件", "全部 4 个 PE 与 12,511 文件 0 命中", "E-27"),
 ("REFUTED", "Q-86", "对端实现可直接适用 2697", "对端引用地址属另一构建", "E-27"),
 ("REFUTED", "Q-91", "bds/demonware 命中为协议证据", "均为字节巧合/致谢表", "E-27"),
 ("REFUTED", "Q-101", "参考对端无客户端 codec 层", "C# 路径 DecodeKey 与之逐字节一致（新增 Q-108）", "CODEC-KEYFLOW-001"),
 ("REFUTED", "Q-109", "更正常数两处措辞与 .tvm0 VA", "6AB310=VA、5F0/5F4=provider 指针、.tvm0 VA=0x0DD58000", "CODEC-KEYFLOW-001"),
 ("BLOCKED", "Q-111", ".tvm0 完整语义", "未逐指令还原（交集检查为 0 命中）", "CODEC-KEYFLOW-001"),
]
for a,b,c,e,f in hist:
    A("| %s | %s | %s | %s | %s |" % (a,b,c,e,f))
A("")
A("## 5. 声明")
A("")
A("- 本登记簿为**只读汇总**，不新增、不删除任何条目，不改变任何权重与评分口径。")
A("- `NOT-OBSERVED` 表示**未做实时互操作验证**；本轮所有结论均为静态。")
A("- 认知完备率上升来自对既有 BLOCKED 链条的真实解析，非口径放宽。")

open(os.path.join(OUT,"00_CONSOLIDATED_QUESTION_REGISTER.md"),"w",encoding="utf-8").write("\n".join(L)+"\n")
print("register md written, lines", len(L))
