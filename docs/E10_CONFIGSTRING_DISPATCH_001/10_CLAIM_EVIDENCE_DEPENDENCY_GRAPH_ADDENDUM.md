# 10 — 结论—证据依赖图（E-10 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\21_CLAIM_EVIDENCE_GRAPH.md`。
> 规则：同一底层证据重复引用只算一个来源。

---

```
◆ C-10-01  0xA2660 有且仅有 3 个直接调用点
   └─✔ EV-10-01（指令级 3 / 字节级 3 / 数据指针 0）
        └─○ 线性扫描含重同步（t01_xref_scan.py）
        └─○ 数据指针全镜像扫描

◆ C-10-02  C2/C3 属 0x352F80，E-09 归属错误
   ├─✔ EV-10-02（调用点函数入口）
   └─✔ EV-10-17（0x352E80 于 0x352F2A ret 后 int3）

◆ C-10-03  客户端存在 9 项外层分派器 0x354100
   ├─✔ EV-10-03（cmp 8 + jmp [eax*4+0x7547AC]，表项 9）
   └─✔ EV-10-04（0x3547D0 读 1 字节键并循环调用）

◆ C-10-04  Configstring body 对应 case 6
   ├─✔ EV-10-05（case 6 → 4 字节长度 + 载荷 → 0x352F80 → 0xA2660）
   ├─✔ EV-10-13（0xA2480 的 10/7/4/12 bit）
   └─⚠ case 4 语义（1 字节 + 3-float）与 Configstring 字段不符（反证）

◆ C-10-05  Configstring body 字段顺序与服务端一致
   ├─✔ EV-10-13（客户端 A3 位宽）
   ├─✔ EV-10-14/15（客户端字节/位读取原语）
   └─✔ E-09 EV-08-01（服务端字段序）

◆ C-10-06  外层 0x04 分派 = 进入 0xA2660 前跳过 1 字节
   ├─✔ EV-10-06（+1 字节，DIRECT）
   ├─✔ EV-10-07/08（服务端 WriteByte(4) 为 1 字节，DIRECT）
   └─⚠ EV-10-16（无 `cmp == 4`）—— **依赖未满足，结论只能 STRONG_INFERENCE / BLOCKED**

◆ C-10-07  0x06 写入侧为 1 字节且位于 body 之后
   ├─✔ EV-10-08（WriteByte = 1 字节）
   └─✔ EV-10-09/10（位同步与 WriteData/WriteLenStr 行为）

◆ C-10-08  0x06 读取侧 8bit / 对齐 / 终止
   ├─✔ EV-10-12（0xA2660 内无 0x06 读取）
   └─⚠ EV-10-16（无 `cmp == 6`）—— **依赖未满足，三项全部 BLOCKED**

◆ C-10-09  count1 = 2 字节
   ├─✔ 客户端：`push 2` + `MSG_ReadData` + `movsx word`
   └─✔ 服务端：`WriteShort` 中 `mov ecx,2`
```

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-10-06 外层 `0x04` | 无 `cmp == 4`，键语义未定 | BLOCKED |
| C-10-08 `0x06` | 无客户端读取点 | BLOCKED |
