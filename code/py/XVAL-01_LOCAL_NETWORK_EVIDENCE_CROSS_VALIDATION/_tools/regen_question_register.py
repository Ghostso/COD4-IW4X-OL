# -*- coding: utf-8 -*-
# Recompute the unified question register from the raw Q-definitions of E-15..E-19,
# using the E-15 weight scale. Produces a single authoritative ledger.
import csv, os
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = rf"{ROOT}\XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION"
W = {"I4":8,"I3":5,"I2":3,"I1":1}
def score(grade):
    return {"PROVEN":1.0,"INFERRED_STRONG":0.6,"INFERRED_WEAK":0.3,"BLOCKED":0.0,"REFUTED":0.0,"CLOSED_NON_GAME":1.0}[grade]
# Q rows: (Q, layer, question, impact, grade, origin)
Q = [
 ("Q-01","传输","游戏协议走哪条传输栈","I4","BLOCKED","E-15"),
 ("Q-02","传输","实时收包→应用层分派的调用边","I4","BLOCKED","E-15"),
 ("Q-03","消息","实时消息外层分帧（长度/头部）","I4","BLOCKED","E-15"),
 ("Q-04","消息","实时消息类型分派器（opcode 表）","I4","BLOCKED","E-15"),
 ("Q-05","Gamestate","实时 Gamestate 0x03 消费者","I4","BLOCKED","E-15"),
 ("Q-06","Configstring","Configstring 子帧识别（0x04 值级）","I3","BLOCKED","E-15"),
 ("Q-07","Configstring","Configstring body reader 实时归属（0xA2660）","I3","BLOCKED","E-15"),
 ("Q-08","Configstring","子帧尾 0x06 读取/对齐/终止","I3","BLOCKED","E-15"),
 ("Q-09","Configstring","count1/A1/A2/A3 字段序","I3","PROVEN","E-15"),
 ("Q-10","Configstring","A2 计数字宽（11 bit）","I2","PROVEN","E-15"),
 ("Q-11","可靠命令","Reliable Command 0x01/0x02 字段序","I4","PROVEN","E-15"),
 ("Q-12","Gamestate","服务端 Gamestate 字段序","I4","PROVEN","E-15"),
 ("Q-13","传输","CODOL 分片层常量（1161/0x70CC729）","I3","PROVEN","E-15"),
 ("Q-14","传输","TLS/libcurl 链归属（更新模块）","I2","CLOSED_NON_GAME","E-15"),
 ("Q-15","工程","网络虚表构造者（0x898588/0x898590）","I2","PROVEN","E-15"),
 ("Q-16","工程","0x67F5F0 真实函数边界","I1","BLOCKED","E-15"),
 ("Q-17","传输","0x1B0430 归属（ICMP ping）","I2","PROVEN","E-16"),
 ("Q-18","工程","0x78772D 归属（时间戳工具）","I1","PROVEN","E-16"),
 ("Q-19","消息","剩余 recv/recvfrom 调用点归属","I4","BLOCKED","E-16"),
 ("Q-20","传输","0x6B4DE0 归属（Demonware recvfrom 封装）","I2","PROVEN","E-17"),
 ("Q-21","传输","0x784F60 归属（Demonware recv 封装）","I2","PROVEN","E-17"),
 ("Q-22","传输","Demonware 栈是否为游戏会话路径","I3","BLOCKED","E-17"),
 ("Q-23","传输","0x775A50/0x775AB0 虚表归属","I4","PROVEN","E-17"),
 ("Q-24","传输","0x898588/0x898590 槽位身份","I2","PROVEN","E-18"),
 ("Q-25","工程","虚表构造者/对象分配","I2","PROVEN","E-18"),
 ("Q-26","传输","libcurl 簇是否为游戏路径","I3","CLOSED_NON_GAME","E-18"),
 ("Q-27","工程","0x776170 的注册者","I1","BLOCKED","E-18"),
 ("Q-28","传输","Demonware 栈是否承载游戏会话","I4","BLOCKED","E-18"),
 ("Q-29","传输","0x6ABBC0 分帧器身份","I3","PROVEN","E-19"),
 ("Q-30","传输","0x6ABE80 状态机身份","I3","PROVEN","E-19"),
 ("Q-31","传输","0x788133 归属","I2","REFUTED","E-19"),
 ("Q-32","传输","Demonware 类型码语义→游戏协议","I4","BLOCKED","E-19"),
 # ---- XVAL-01 additions ----
 ("Q-33","方法学","客户端搜索空间完备性（.data/.tp3/.tvm0）是否可恢复","I4","BLOCKED","XVAL-01"),
 ("Q-34","可靠命令","客户端 0x02→0xA2E50 绑定被独立字节/运行时验证","I4","BLOCKED","XVAL-01"),
 ("Q-35","Configstring","0x04 外层值级识别 + 0x06 客户端读取闭合","I3","BLOCKED","XVAL-01"),
 ("Q-36","握手","COOKIE_ECHO 189 vs 219 对目标客户端的裁决","I3","BLOCKED","XVAL-01"),
 ("Q-37","证据治理","项目内跨报告主张的一致性（无静默漂移）","I2","INFERRED_STRONG","XVAL-01"),
 ("Q-38","开源","开源实现可迁移边界被显式化","I2","PROVEN","XVAL-01"),
]
rows=[]
total=0; gained=0.0; by_impact={}
for q in Q:
    layer,question,imp,grade,origin = q[1],q[2],q[3],q[4],q[5]
    w=W[imp]; s=score(grade); contrib=w*s
    total+=w; gained+=contrib
    rows.append(dict(Q_ID=q[0],Protocol_Layer=layer,Question=question,Impact=imp,Weight=w,
                     Current_Grade=grade,Score=s,Weighted_Contribution=round(contrib,3),
                     Origin_Task=origin))
    d=by_impact.setdefault(imp,[0,0.0]); d[0]+=w; d[1]+=contrib
rate = gained/total
# historical ledger (as each task reported it) for comparison
hist=[("E-15",91,32,32/91),("E-16",103,36,36/103),("E-17(reported)",114,42,42/114),
      ("E-17/E-18-continuity",122,42,42/122),("E-18",142,53,53/142),("E-19",163,66,66/163)]
with open(rf"{OUT}\XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md","w",encoding="utf-8") as f:
    f.write("# XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE — 问题库增补与风险加权重算\n\n")
    f.write("> 继承 E-15 权重标度（I4=8 / I3=5 / I2=3 / I1=1）；解决度映射：PROVEN=1.0、INFERRED(强)=0.6、INFERRED(弱)=0.3、BLOCKED=0.0、REFUTED=0.0、已裁定非游戏(闭合)=1.0。\n")
    f.write("> **口径声明（验收要求）：** 任何完成率必须同时给出**分母、权重、时点**；本表为 XVAL-01 时点。\n")
    f.write("> 本表**不静默改写**历史分母；历史差异在 §3 显式登记（见 `XVAL01_CONFLICT_REGISTER.md` CONF-X07/X08）。\n\n")
    f.write("## 1. 权威账本（逐项可复算）\n\n")
    f.write("| Q ID | 层 | 问题 | 影响 | 权重 | 当前等级 | 解决度 | 加权贡献 | 来源任务 |\n")
    f.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['Q_ID']} | {r['Protocol_Layer']} | {r['Question']} | {r['Impact']} | {r['Weight']} | {r['Current_Grade']} | {r['Score']:.1f} | {r['Weighted_Contribution']:.1f} | {r['Origin_Task']} |\n")
    f.write(f"\n**总权重（分母）= {total}**　**加权得分 = {gained:.1f}**　**风险加权解决率 = {gained:.1f}/{total} = {rate*100:.2f}%**\n\n")
    f.write("### 按影响等级拆分\n\n| 等级 | 权重和 | 得分 | 解决度 |\n|---|---|---|---|\n")
    for imp in ["I4","I3","I2","I1"]:
        if imp in by_impact:
            tw,tg=by_impact[imp]; f.write(f"| {imp} | {tw} | {tg:.1f} | {tg/tw*100:.1f}% |\n")
    f.write("\n")
    f.write("## 2. XVAL-01 新增问题（Q-33..Q-38）\n\n")
    f.write("| Q ID | 问题 | 影响 | 权重 | 等级 | 说明 |\n|---|---|---|---|---|---|\n")
    notes={
      "Q-33":"三条结构性缺口（.data 99.86%、.tp3 52.5MB、.tvm0 未解码）——决定所有客户端 BLOCKED 的根因",
      "Q-34":"0x02 分派绑定；本任务仍未闭合，且搜索空间不完备",
      "Q-35":"0x04 值级 + 0x06 客户端读取；仍可纯静态推进",
      "Q-36":"握手长度冲突；需抓包",
      "Q-37":"跨报告一致性；本任务已复核主要主张（C-001..C-040），多数一致，发现账目漂移 CONF-X07/X08",
      "Q-38":"可迁移性边界已显式化（开源审计）",
    }
    for r in rows:
        if r["Origin_Task"]=="XVAL-01":
            f.write(f"| {r['Q_ID']} | {r['Question']} | {r['Impact']} | {r['Weight']} | {r['Current_Grade']} | {notes[r['Q_ID']]} |\n")
    f.write("\n## 3. 历史分母轨迹（含两处不一致，保留双述）\n\n")
    f.write("| 轮次 | 分母 | 加权得分 | 解决率 | 备注 |\n|---|---|---|---|---|\n")
    for name,tw,tg,rt in hist:
        f.write(f"| {name} | {tw} | {tg} | {rt*100:.2f}% | {'与 E-17 自述 114 不一致（E-18 用 122）' if name=='E-17/E-18-continuity' else ''} |\n")
    f.write(f"\n> **XVAL-01 权威分母 = {total}**（在 E-19 的 163 基础上新增 Q-33..Q-38 的 8+8+5+3+3+3=30 → 163+30={total}）。\n")
    f.write("> 复算方式：`_tools\\regen_question_register.py`（本任务可执行，输出本表）。不得只报百分比而省略分母。\n\n")
    f.write("## 4. 与历史记录的关系\n\n")
    f.write("- E-15 权重标度：直接继承（未改）。\n- E-16/E-17/E-18/E-19：分母扩展，本任务**未改写**其结论。\n")
    f.write("- E-17 自述 114、E-18 引用 122：**双方保留**（CONF-X07），本表以统一重算消解跨轮引用问题。\n")
with open(rf"{OUT}\_data\question_register_recompute.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow(r)
print(f"total_weight={total} score={gained:.1f} rate={rate*100:.2f}%  Q={len(rows)}")
for imp in ["I4","I3","I2","I1"]:
    if imp in by_impact:
        tw,tg=by_impact[imp]; print(f"  {imp}: weight={tw} score={tg:.1f} rate={tg/tw*100:.1f}%")
