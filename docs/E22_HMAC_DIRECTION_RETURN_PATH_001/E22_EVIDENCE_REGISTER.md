# E22 证据登记

| 证据 ID | 类型 | 地址/RVA | 内容 | 等级 |
|---|---|---|---|---|
| EV-E22-01 | 调用约定 | 0x6AC0C0 | thiscall，两个输出参数，ret 8 | PROVEN |
| EV-E22-02 | 调用点 | 0x6AC2F0 | 唯一调用 0x6AAE70，五参数，ret 0x14 | PROVEN |
| EV-E22-03 | 分支 | 0x6AC2D9..0x6AC2F7 | 0x85 进入 HMAC 路径，AL 写入输出状态 | PROVEN |
| EV-E22-04 | 计数器 | 0x6AAFA4..0x6AAFB9 | 读/递增 +0x5D0，比较失败置 Bad recv counter | PROVEN |
| EV-E22-05 | 比较 | 0x6AB0E6..0x6AB12D | 16 字节 XOR/OR 比较，失败置 HMAC mismatch | PROVEN |
| EV-E22-06 | 失败状态 | 0x6AAFD8 → 0xAAA770 | 失败调用日志并置连接状态 4 | PROVEN |
| EV-E22-07 | 映射 | 0xA85AD0 等 | 位于 .data BSS，RawSize 外，磁盘无字节 | PROVEN |
| EV-E22-08 | 调用者 | 0x68EEF1 / 0x68F02C | 会话循环调用 0x6AC3D0 → 0x6AC0C0 | PROVEN |

## 历史更正

E21 声称下游目标位于 `.tvm0`；E22 以节区头部与 RawSize 重新核验后更正为 `.data` BSS 虚拟尾部。此更正不删除 E21 原文。
