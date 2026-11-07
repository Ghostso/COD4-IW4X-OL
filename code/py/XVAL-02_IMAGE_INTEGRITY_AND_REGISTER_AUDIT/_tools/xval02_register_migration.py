# -*- coding: utf-8 -*-
"""XVAL-02 统一问题库迁移审计（权威版）。
- 读取 E-15..E-19 的历史问题登记（逐项，含各自自报汇总）
- 读取 XVAL-01 权威账本
- 用统一权重/解决度映射独立复算历史链，与自报值对账
- 逐项登记 新增/合并/关闭/重新评级/权重调整
- 输出最终账本（XVAL-02 时点）与对账表
不修改任何历史文件。"""
import csv, json, os
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT  = rf"{ROOT}\XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT"
X1   = rf"{ROOT}\XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION"
W  = {"I4":8,"I3":5,"I2":3,"I1":1}
SC = {"PROVEN":1.0,"INFERRED_STRONG":0.6,"INFERRED_WEAK":0.3,"BLOCKED":0.0,"REFUTED":0.0,"CLOSED":1.0,"CLOSED_NON_GAME":1.0,"INFERRED":0.3}

HIST = {
 "E-15": dict(rep_total=91, rep_score=32, qs=[
   ("Q-01","传输","游戏协议走哪条传输栈","I4","BLOCKED"),("Q-02","传输","实时收包→应用层分派调用边","I4","BLOCKED"),
   ("Q-03","消息","实时消息外层分帧","I4","BLOCKED"),("Q-04","消息","实时消息类型分派器","I4","BLOCKED"),
   ("Q-05","Gamestate","实时 Gamestate 0x03 消费者","I4","BLOCKED"),("Q-06","Configstring","Configstring 子帧识别(0x04)","I3","BLOCKED"),
   ("Q-07","Configstring","Configstring body reader 实时归属","I3","BLOCKED"),("Q-08","Configstring","子帧尾 0x06 读取/对齐/终止","I3","BLOCKED"),
   ("Q-09","Configstring","count1/A1/A2/A3 字段序","I3","PROVEN"),("Q-10","Configstring","A2 计数字宽(11bit)","I2","PROVEN"),
   ("Q-11","可靠命令","Reliable Command 0x01/0x02 字段序","I4","PROVEN"),("Q-12","Gamestate","服务端 Gamestate 字段序","I4","PROVEN"),
   ("Q-13","传输","CODOL 分片层常量","I3","PROVEN"),("Q-14","传输","TLS/libcurl 链归属","I2","CLOSED"),
   ("Q-15","工程","网络虚表构造者 0x898588/0x898590","I2","BLOCKED"),   # <-- E-15 原始为 BLOCKED
   ("Q-16","工程","0x67F5F0 真实函数边界","I1","BLOCKED")]),
 "E-16": dict(rep_total=103, rep_score=36, qs=[
   ("Q-17","传输","0x1B0430 归属(ICMP)","I2","PROVEN"),("Q-18","工程","0x78772D 归属(时间戳工具)","I1","PROVEN"),
   ("Q-19","消息","剩余 recv/recvfrom 调用点归属","I4","BLOCKED")]),
 "E-17": dict(rep_total=122, rep_score=42, alt_total=114, qs=[
   ("Q-20","传输","0x6B4DE0 归属","I2","PROVEN"),("Q-21","传输","0x784F60 归属","I2","PROVEN"),
   ("Q-22","传输","Demonware 栈是否为游戏会话路径","I3","BLOCKED"),
   ("Q-23","传输","0x775A50/0x775AB0 虚表归属","I4","BLOCKED")]),   # E-17 原始 BLOCKED
 "E-18": dict(rep_total=142, rep_score=53, alt_total=133, qs=[
   ("Q-24","传输","0x898588/0x898590 槽位身份(=Q-15)","I2","PROVEN"),("Q-25","工程","虚表构造者/对象分配","I2","PROVEN"),
   ("Q-26","传输","libcurl 簇是否为游戏路径","I3","CLOSED"),
   ("Q-27","工程","0x776170 的注册者","I1","BLOCKED"),("Q-28","传输","Demonware 栈是否承载游戏会话","I4","BLOCKED")]),
 "E-19": dict(rep_total=163, rep_score=66, alt_total=142, qs=[
   ("Q-29","传输","0x6ABBC0 分帧器身份","I3","PROVEN"),("Q-30","传输","0x6ABE80 状态机身份","I3","PROVEN"),
   ("Q-31","传输","0x788133 归属","I2","CLOSED"),("Q-32","传输","Demonware 类型码语义→游戏协议","I4","BLOCKED")]),
}

def wsum(pairs): return sum(W[p[3]] for p in pairs)
def ssum(pairs): return sum(W[p[3]]*SC[p[4]] for p in pairs)

# ---- 1. 历史链对账 ----
recon=[]
run=[]; runw=0; runs=0.0
for t in ["E-15","E-16","E-17","E-18","E-19"]:
    run += HIST[t]["qs"]; runw=wsum(run); runs=ssum(run)
    recon.append(dict(Task=t,Recomputed_Total=runw,Recomputed_Score=round(runs,3),
        Recomputed_Rate=round(runs/runw*100,3),Reported_Total=HIST[t]["rep_total"],Reported_Score=HIST[t]["rep_score"],
        Reported_Rate=round(HIST[t]["rep_score"]/HIST[t]["rep_total"]*100,3),
        Total_Match=(runw==HIST[t]["rep_total"]),Score_Match=(abs(runs-HIST[t]["rep_score"])<1e-6),
        Alt_Reported_Total=HIST[t].get("alt_total","")))
hist_ok = all(r["Total_Match"] for r in recon)

# ---- 2. 迁移登记（逐项） ----
cols=["Stable_ID","Origin_Task","Protocol_Layer","Question","Change_Type",
      "Hist_Impact","Hist_Weight","Hist_Grade","Hist_Weighted",
      "XVAL01_Impact","XVAL01_Weight","XVAL01_Grade","XVAL01_Weighted",
      "XVAL02_State","XVAL02_Weight","XVAL02_Score","XVAL02_Weighted","Delta_vs_Hist","Basis","Evidence"]
x1={r["Q_ID"]:r for r in csv.DictReader(open(rf"{X1}\_data\question_register_recompute.csv",encoding="utf-8-sig"))}
# XVAL-02 决策
MERGES={"Q-15":"并入 Q-24（同一对象 0x898588/0x898590；XVAL-01 静默改判为 PROVEN 且与 Q-24 重复计数）",
        "Q-22":"并入 Q-28/Q-32 家族（同一 Demonware-游戏绑定问题，逐轮细化）"}
CLOSES={"Q-19":"E-17 归位 0x6B4DE0/0x784F60、E-18 归位 0x775A50/0x775AB0、E-19 归位 0x788133 → 9/9 收包点全部归属，可关闭",
        "Q-23":"E-18 已判定 0x898588/0x898590=libcurl vtable（含构造者）→ PROVEN"}
REGRADE_X2={"Q-33":("REFUTED","'99.86%缺失' 被驳：.data 原始字节与打包件逐字节同一；尾部为 BSS 零填"),
            "Q-37":("INFERRED_WEAK","发现框架误用(C-037)与两处账目漂移 → 一致性下调")}
ops=[]
for t in ["E-15","E-16","E-17","E-18","E-19"]:
    for qid,layer,q,imp,g in HIST[t]["qs"]:
        hw=W[imp]; hs=SC[g]; hc=hw*hs
        r=x1.get(qid)
        x1w=int(r["Weight"]) if r else ""; x1g=r["Current_Grade"] if r else ""; x1c=float(r["Weighted_Contribution"]) if r else ""
        # XVAL-02 state
        if qid in MERGES:
            v2w=0; v2s=0.0; v2g="MERGED"; ct="MERGED"
        elif qid in CLOSES:
            v2w=W[imp]; v2g="CLOSED"; v2s=1.0; ct=("CLOSED" if g=="BLOCKED" else "RETAINED")
        elif qid in REGRADE_X2:
            v2w=int(r["Weight"]) if r else W[imp]; v2g=REGRADE_X2[qid][0]; v2s=SC[v2g]; ct="REGRADED(XVAL-02)"
        else:
            v2w=int(r["Weight"]) if r else W[imp]; v2g=r["Current_Grade"] if r else g; v2s=SC[v2g]
            ct="RETAINED"
        if x1g and x1g!=g and ct=="RETAINED": ct="REGRADED(XVAL-01)"
        if qid=="Q-23": ct="REGRADED(XVAL-01)"  # E-17 BLOCKED -> XVAL-01 PROVEN
        basis = MERGES.get(qid) or CLOSES.get(qid) or (REGRADE_X2.get(qid,("",""))[1]) or "状态延续"
        ops.append(dict(Stable_ID=qid,Origin_Task=t,Protocol_Layer=layer,Question=q,Change_Type=ct,
            Hist_Impact=imp,Hist_Weight=hw,Hist_Grade=g,Hist_Weighted=round(hc,3),
            XVAL01_Impact=(r["Impact"] if r else ""),XVAL01_Weight=x1w,XVAL01_Grade=x1g,XVAL01_Weighted=x1c,
            XVAL02_State=v2g,XVAL02_Weight=v2w,XVAL02_Score=v2s,XVAL02_Weighted=round(v2w*v2s,3),
            Delta_vs_Hist=round(v2w*v2s-hc,3),Basis=basis,Evidence="E-15..E-19 / XVAL-01 / XVAL-02 审计"))
# XVAL-01 新增
for qid,r in x1.items():
    if r["Origin_Task"]=="XVAL-01":
        v2g=REGRADE_X2.get(qid,(r["Current_Grade"],""))[0]; v2s=SC[v2g]; v2w=int(r["Weight"])
        ops.append(dict(Stable_ID=qid,Origin_Task="XVAL-01",Protocol_Layer=r["Protocol_Layer"],Question=r["Question"],
            Change_Type=("REGRADED(XVAL-02)" if qid in REGRADE_X2 else "NEW(XVAL-01)"),
            Hist_Impact="",Hist_Weight="",Hist_Grade="",Hist_Weighted="",
            XVAL01_Impact=r["Impact"],XVAL01_Weight=r["Weight"],XVAL01_Grade=r["Current_Grade"],XVAL01_Weighted=r["Weighted_Contribution"],
            XVAL02_State=v2g,XVAL02_Weight=v2w,XVAL02_Score=v2s,XVAL02_Weighted=round(v2w*v2s,3),Delta_vs_Hist="",
            Basis=(REGRADE_X2.get(qid,("",""))[1] or "XVAL-01 新增"),Evidence="XVAL01_UNIFIED_QUESTION_REGISTER_UPDATE.md"))
# XVAL-02 新增
X2NEW=[("Q-39","传输","打包端 .text/.tvm0 的 aplib 保真性可独立验证","I2","PROVEN","NEW(XVAL-02)","aplib(strict) 复现 .text 8,047,104B 与 .tvm0 2,853,888B，orig CRC 通过"),
       ("Q-40","方法学","是否曾把 PE 节区尺寸比误用为内容缺失证据","I2","PROVEN","NEW(XVAL-02)","'99.86%缺失'框架被驳；确立字节级判据"),
       ("Q-41","证据治理","REFUTED 解决度映射跨任务是否一致","I2","BLOCKED","NEW(XVAL-02)","E-15: REFUTED=0.0；E-18/E-19 将闭合项计 1.0 —— 口径不一致"),
       ("Q-42","镜像","末节 .tp3（VS 52.5MB）未恢复是否掩盖游戏代码","I3","BLOCKED","NEW(XVAL-02)","VSize 0x03214000 vs Raw 0x336800；恢复镜像同址改置 .rimp 修复表"),
       ("Q-43","镜像","BSS 尾部（208.1MB loader 零填）能否静态隐藏分派表","I3","BLOCKED","NEW(XVAL-02)","Char 0xC0000040 + VS>>Raw → 隐式 BSS，运行时内容不可静态获得")]
for qid,layer,q,imp,g,ct,basis in X2NEW:
    ops.append(dict(Stable_ID=qid,Origin_Task="XVAL-02",Protocol_Layer=layer,Question=q,Change_Type=ct,
        Hist_Impact="",Hist_Weight="",Hist_Grade="",Hist_Weighted="",
        XVAL01_Impact="",XVAL01_Weight="",XVAL01_Grade="",XVAL01_Weighted="",
        XVAL02_State=g,XVAL02_Weight=W[imp],XVAL02_Score=SC[g],XVAL02_Weighted=round(W[imp]*SC[g],3),
        Delta_vs_Hist="",Basis=basis,Evidence="XVAL02_IMAGE/REGISTER AUDIT"))

with open(rf"{OUT}\XVAL02_QUESTION_REGISTER_MIGRATION.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in ops: w.writerow(r)

# ---- 3. 最终账本与阶段对账 ----
def stage(pairs):
    tw=sum(W[p[3]] for p in pairs); ts=sum(W[p[3]]*SC[p[4]] for p in pairs); return tw,round(ts,3)
base=[]
for t in ["E-15","E-16","E-17","E-18","E-19"]: base+=HIST[t]["qs"]
e19w,e19s=stage(base)

# XVAL-01 stage from its ledger (38 items)
x1rows=list(csv.DictReader(open(rf"{X1}\_data\question_register_recompute.csv",encoding="utf-8-sig")))
x1w=sum(int(r["Weight"]) for r in x1rows); x1s=sum(float(r["Weighted_Contribution"]) for r in x1rows)
# XVAL-02 stage
v2=[(r["Stable_ID"],r["Protocol_Layer"],r["XVAL02_Weight"],None) for r in ops]
def stage2():
    tw=0; ts=0.0
    for r in ops:
        if r["XVAL02_Weight"]=="": continue
        tw+=int(r["XVAL02_Weight"]); ts+=float(r["XVAL02_Weighted"])
    return tw,round(ts,3)
v2w,v2s=stage2()
# I4
i4w=sum(int(r["XVAL02_Weight"]) for r in ops if r["XVAL02_Weight"]!="" and (r["Hist_Impact"]=="I4" or r["XVAL01_Impact"]=="I4"))
i4s=sum(float(r["XVAL02_Weighted"]) for r in ops if r["XVAL02_Weight"]!="" and (r["Hist_Impact"]=="I4" or r["XVAL01_Impact"]=="I4"))
stages=[("E-15 (原始)",HIST["E-15"]["rep_total"],HIST["E-15"]["rep_score"]),
        ("E-19 (原始累计)",e19w,e19s),
        ("XVAL-01 发布值",x1w,x1s),
        ("XVAL-02 最终",v2w,v2s)]
summary=dict(hist_chain_reconciles=hist_ok, i4_weight=i4w, i4_score=round(i4s,3),
  stages=[dict(name=n,total=t,score=s,rate=round(s/t*100,3)) for n,t,s in stages],
  e19_genuine_rate=round(e19s/e19w*100,3), xval01_rate=round(x1s/x1w*100,3), xval02_rate=round(v2s/v2w*100,3))
json.dump(dict(summary=summary,recon=recon,
  changes={r["Stable_ID"]:r["Change_Type"] for r in ops if r["Change_Type"] not in ("RETAINED","NEW(XVAL-01)","NEW(XVAL-02)")}),
  open(rf"{OUT}\_data\register_recalc.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)

print("### 历史链对账（独立复算 vs 自报）###")
for r in recon:
    print(f"  {r['Task']}: 复算 {r['Recomputed_Total']}/{r['Recomputed_Score']} = {r['Recomputed_Rate']}%  |  自报 {r['Reported_Total']}/{r['Reported_Score']} = {r['Reported_Rate']}%  | total匹配={r['Total_Match']} score匹配={r['Score_Match']} alt={r['Alt_Reported_Total']}")
print(f"  历史链 total 全部匹配 = {hist_ok}")
print("\n### 阶段对账 ###")
for n,t,s in stages: print(f"  {n:<22} {t}/{s} = {s/t*100:.3f}%")
print(f"\n### XVAL-02 最终 ###  I4 = {i4w}/{round(i4s,3)} = {i4s/i4w*100:.3f}%")
print("\n### 非 RETAINED 变更 ###")
for r in ops:
    if r["Change_Type"] not in ("RETAINED",): print(f"  {r['Stable_ID']:<6} {r['Change_Type']:<20} {r['Basis'][:70]}")


