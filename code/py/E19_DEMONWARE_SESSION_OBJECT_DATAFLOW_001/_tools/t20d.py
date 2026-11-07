import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001"
F={}
F["E19_EVIDENCE_REGISTER.md"]="""# E19 — 证据登记 / EVIDENCE REGISTER

> 新增证据 ID（E-19 系列）。全部来自本轮自建脚本与恢复镜像原始字节。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-19-01 | FRAMING | RVA 0x6ABBC0 | 4 字节长度前缀帧读取器：累计 [esi+0xA4]，满 4 后调 0x6878A0 解析长度到 [esi+0xAC] | out_6abbc0.txt | PROVEN |
| EV-19-02 | BOUNDS | RVA 0x6878A0 | 边界检查（cmp/setbe）+ memcpy；非长度解析器 | out_parse.txt | PROVEN |
| EV-19-03 | STATEMACHINE | RVA 0x6ABE80 | 4 状态接收状态机：jmp [ebx*4+0xAAC090]；状态字段 [esi+0x9C] | out_caller.txt | PROVEN |
| EV-19-04 | TABLE | RVA 0x6AC090 | 跳转表：0→0x6ABE99、1→0x6ABF1D、2→0x6ABF47、3→0x6ABF52 | out_state.txt | PROVEN |
| EV-19-05 | TYPECODE | RVA 0x6A9920 | 读 1 字节类型码到 [esi+0xA8]；cmp al,1 → size 1；cmp al,2 → size 9 | out_payload.txt | PROVEN |
| EV-19-06 | OBJECT | RVA 0x6ABE99 | 状态重置：清 +0xA4/+0xA8/+0xAC；operator delete[] + 虚析构释放 +0xB0/+0xB4 | out_caller.txt | PROVEN |
| EV-19-07 | CONNSTATE | RVA 0x6AA770 | 连接状态 [esi+0xC8]（1/2/4）；清理时置 4 并 jmp 0xB83B90 | out_caller.txt | PROVEN |
| EV-19-08 | UNIQUE | RVA 0x6ABBC0 | 唯一直接调用者 0x6ABF1F；无数据指针引用 | out_true.txt | PROVEN |
| EV-19-09 | RECV | RVA 0x788133 | recv 直接调用点（非 thunk）；错误码 0x2733 处理两次 | out_state.txt | PROVEN |
| EV-19-10 | BOUNDARY | RVA 0x787B2F | 0x788133 真实 prologue 在 0x787B2F 附近；更正 E-16 的 0x78772D 标注 | out_t07_788 | PROVEN |
| EV-19-11 | NULL | 0x6ABBC0 闭包(4)=48 | 不含 0xA2660/0xA2E50/0x350170/0x3547D0/0x354100 | out_t07_788 | PROVEN（负） |
| EV-19-12 | NULL | 0x6ABBC0 vs 0x78772D 段 | 共享下游仅 3 个通用工具函数（0x749B31/0x3622AC/0x755F08） | out_t07_788 | PROVEN（负） |
| EV-19-13 | CTOR | RVA 0x6ABBC0 对象 | 构造函数/分配点未定位（扫描立即数 + 数据指针均无写入 vptr 的证据） | out_true.txt | BLOCKED |
| EV-19-14 | HASH | 三样本 | 冻结基线开工/收工各复核一次，均一致 | Get-FileHash | PROVEN |
"""
F["E19_HYPOTHESIS_LEDGER.md"]="""# E19 — 假设台账 / HYPOTHESIS LEDGER

---

### H-E19-01：0x6ABBC0 是 4 字节长度前缀帧读取器
- 支持：累计 [esi+0xA4]；满 4 后 0x6878A0 解析；长度写 [esi+0xAC]（EV-19-01/02）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-02：0x6ABE80 是 4 状态接收状态机
- 支持：jmp [ebx*4+0xAAC090]；状态字段 [esi+0x9C]（EV-19-03/04）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-03：0x6A9920 读 1 字节类型码并二值分派
- 支持：mov al,[edi]；cmp al,1 / cmp al,2；size 1/9（EV-19-05）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-04：该状态机承载 CODOL 游戏消息
- 支持：（无直接证据）
- 反证：类型码域为 {1,2} 二值，与游戏顶层 opcode 1..4 + 子帧 0..8 不同；4 层闭包不含任何游戏解析候选（EV-19-11）
- 状态：BLOCKED（未证，未完全否证）
- 下一步：解出类型码 1/2 的语义；展开 [esi+0xB0]/[esi+0xB4] 对象类型

### H-E19-05：0x6ABBC0 对象是 Demonware 会话对象
- 支持：与 DW-Client-Ticket / bdSessionParams 同簇（E-17）；调用 0xB83B70（Demonware recv 封装）
- 反证：无类型名到函数的直接绑定
- 状态：STRONG_INFERENCE

### H-E19-06：0x788133 与 0x6ABBC0 同路径
- 支持：（无）
- 反证：无调用边/数据流；共享下游仅通用工具（EV-19-12）
- 状态：REFUTED（限定范围）

### H-E19-07：0x788133 属 0x78772D（E-16 标注）
- 支持：（prologue 启发式）
- 反证：真实 prologue 在 0x787B2F 附近（EV-19-10）
- 状态：REFUTED

### H-E19-08：该会话对象与游戏解析候选连接
- 支持：（无）
- 反证：4 层闭包不含任何已知候选（EV-19-11）
- 状态：REFUTED（限定范围）

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-18 libcurl vtable 不承载游戏协议 | 保留 |
| E-16 0x1B0430 属 ICMP ping | 保留 |
| E-15 TLS 栈属 HTTP 更新 | 保留 |
| E-13 0x3524F0 是发送暂存 | 保留 |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
