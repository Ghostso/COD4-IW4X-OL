# CODOL 帧长度兼容性审计（001）

> 任务：`CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001`
> 范围：只读审计本地 parser 的 `0x100000` 上限与冻结客户端密文长度约束；不启动游戏或服务端，不注入，不联网，不修改 parser。
> 运行状态：实时互通仍为 **NOT-OBSERVED**。

## 1. 结论摘要

| 项 | 结论 | 状态 |
|---|---|---|
| 本地 parser 上限位置 | `REF_LOBBY_KIT/codol_crypto.py::parse_frames`，条件是外层 `ln > 0x100000` | `CONFIRMED-STATIC` |
| 冻结客户端长度检查位置 | `0x00AAAF7B` 检查密文 16B 对齐；`0x00AAAF80` 检查 `ecx < 0xFFFFFF` | `CONFIRMED-STATIC` |
| 被比较的量 | 客户端 `ecx` 为 `tag_address - ciphertext_start`，即密文长度，不是外层 `u32len` | `CONFIRMED-STATIC` |
| 最大合法密文 | 最大 16B 对齐且 `< 0xFFFFFF` 的密文长度为 `0xFFFFF0` | `CONFIRMED-STATIC` |
| 对应的最大外层 `u32len` | `0xFFFFF0 + 0x1E = 0x100000E` | `CONFIRMED-STATIC` |
| 本地 parser 最大可接受外层值 | `0x100000`（数值条件），但最大 16B 对齐合法帧的 `u32len` 为 `0xFFFFE` | `CONFIRMED-STATIC` |
| 差异区间 | 有效的 16B 对齐外层长度从 `0x10000E` 开始；客户端静态可继续到 `0x100000E`；本地 parser 拒绝这段 | `CONFIRMED-STATIC` |
| 现有目标兼容性影响 | 固定小帧向量不受影响；大于 1MiB 的完整帧兼容性未验证 | `UNRESOLVED` |
| 原版阶段行为 | 没有启动客户端或服务端，不能在原版运行路径上验证 | `NOT-OBSERVED` |

**不建议直接修改 parser 上限。** 当前证据足以说明“本地 parser 上限更严格且层次不同”，但不足以证明目标使用场景需要超过 `0x100000` 或直接扩展到 `0x100000E`。

## 2. 输入与冻结

| 输入 | SHA-256 |
|---|---|
| `codoMP_client_shipRetail.exe` | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` |
| `codol2697-static-candidate.bin` | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` |
| G3 原始脚本 | `ea3a997a480dd99cce0ab34241aa78402e7a370f5e6ff8bb9ac4f9c244023010` |
| G3 原始结果 CSV | `6a9ea44e67adca4c07848f6a7c757203a750dd2e38b31b864470e3866c872ea9` |
| G3 原始执行日志 | `f26ffdb1108de434ac8a9483a1edf475814e0ec1eede783286544f1cacd3782c` |
| Counter-boundary 审计 | `4a934db18b613c7fadc8dcde0f478d6afb0d2248967db371afd096f211fa946c` |
| Counter-boundary 静态证据 | `55b775bf7a2640c5c276049b049582e7634c526f256e5e1b62595a6047d8992c` |

完整输入哈希和实际执行范围见：

- `_data/length_compatibility_evidence.json`
- `CODOL_LENGTH_BOUNDARY_CASES_001.csv`

## 3. 长度公式及证据来源

### 3.1 0x85/0x86 任务帧的几何关系

```text
frame = u32len | AB | 85 | u32seq | IV16 | ciphertext | tag8
```

| 公式 | 值 | 证据 |
|---|---:|---|
| 固定头到 IV 结束 | `10 + 16 = 26B` | KF-16/KF-17，出站写入点 `0xAAAA10` 及实际帧偏移 |
| tag | `8B` | KF-18，末 8B 截取 |
| 密文对齐 | `ct_len = ceil((5 + payload_len)/16) * 16` | 出站 `lea ebx,[len+0x14]; and ebx,0xF0`；参考 `n=(5+len(inner)+15)//16*16` |
| 外层长度 | `outer_len = ct_len + 30` | `0xAAAA9A..0xAAAA9D`：`temp=ct+0x1E`；参考与抓包一致 |
| 总长 | `total_len = outer_len + 4 = ct_len + 34` | KF-17；固定 10B 前缀 + 16B IV + ct + 8B tag |
| 0x86 最大 payload 对应同一 ct 分组 | `payload_len_max = ct_len - 5` | `ct_len = ceil((5 + payload_len)/16)*16` |

这些公式只描述已确认的 0x85 帧布局；它们不证明原版客户端会接收任意合法长度组合。

### 3.2 外层长度字段

| 项 | 值 | 证据 |
|---|---|---|
| 宽度 | 32-bit | 4B write/read/copy |
| 字节序 | little-endian x86 | 固定向量 request `0x9E 00 00 00`、response `0x3E 00 00 00`；dword copy 无 byteswap |
| 语义 | `u32len = total_len - 4` | KF-17；抓包重编码复现 |
| 上限字段层 | 外层长度字段 | 本地 parser 直接比较 `ln` |

## 4. 本地 parser 限制

实现位置：`D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\codol_crypto.py` 的 `parse_frames`。

相关逻辑：

```python
ln = struct.unpack_from("<I", buf, off)[0]
if ln == 0:
    # keepalive
if ln > 0x100000:
    return frames, buf[off:]
if len(buf) - off - 4 < ln:
    break
frames.append((buf[off:off + 4 + ln], "frame"))
```

因此：

- **数值条件**：`ln <= 0x100000` 才可能被 parser 接受；`ln == 0x100000` 仍满足条件。
- **完整帧条件**：缓冲区必须至少有 `4 + ln` 字节，否则 parser 等待更多数据。
- `0x100000` 是**本地 parser 策略**，本次新发现的客户端约束是密文长度 `< 0xFFFFFF`，两者不是同一字段。
- parser 本身不检查密文 16B 对齐；对齐检查发生在后面的任务帧解码路径。

## 5. 冻结客户端静态长度约束

在 `0x00AAAE70` 中：

```text
0x00AAAF58..0x00AAAF6C  定位 tag 指针，读取末尾 8B
0x00AAAF73..0x00AAAF79  比较 tag 指针与 ciphertext_start
0x00AAAF7B              test cl, 0xF
0x00AAAF80              cmp ecx, 0xFFFFFF
0x00AAAF86              jge -> 长度/帧错误
```

其中 `ecx = tag_address - ciphertext_start`，是密文字节长度。静态约束为：

```text
ct_len > 0
ct_len % 16 == 0
ct_len < 0xFFFFFF
```

最大 16B 对齐合法值：

```text
0xFFFFFF - 1 = 0xFFFFFE
floor(0xFFFFFE / 16) * 16 = 0xFFFFF0
```

对应外层长度和总长：

```text
outer_len_max = 0xFFFFF0 + 30 = 0x100000E
total_len_max = 0x100000E + 4 = 0x1000012
```

**注意**：`cmp ecx,0xFFFFFF` 是客户端单条静态约束；没有运行时端到端样本证明原版服务端会发送到该边界。

## 6. 边界模型结果

详细表：`CODOL_LENGTH_BOUNDARY_CASES_001.csv`。模型只做整数与公式计算，不分配大块帧内存。

| case | 外层 `u32len` | 密文长度 | 16B 对齐 | 本地 parser 数值接受 | 客户端静态长度约束 | 范围判断 |
|---|---:|---:|---|---|---|---|
| LC-01 | `0xFFFFE` | `0xFFFE0` | 是 | 是 | 是 | 本地 cap 下最大的对齐外层值 |
| LC-02 | `0xFFFFF` | `0xFFFE1` | 否 | 是 | 否 | 算术上未对齐，不能形成合法 0x85 帧 |
| LC-03 | `0x100000` | `0xFFFE2` | 否 | 是 | 否 | parser 数值边界本身，不是合法对齐帧边界 |
| LC-04 | `0x100001` | `0xFFFE3` | 否 | 否 | 否 | 本地 parser 确定拒绝；客户端也因未对齐拒绝 |
| LC-05 | `0x10000E` | `0xFFFF0` | 是 | 否 | 是 | 差异区间首个有效对齐外层值 |
| LC-06 | `0xFFFFFF` | `0xFFFFE1` | 否 | 否 | 否 | 旧 G3 外层值不是客户端密文上限的直接同层值 |
| LC-07 | `0x100000E` | `0xFFFFF0` | 是 | 否 | 是 | 客户端静态等价的密文上限边界 |
| LC-08 | `0x100000F` | `0xFFFFF1` | 否 | 否 | 否 | 超出客户端静态最大对齐外层值 |
| LC-09 | `0x1000010` | `0xFFFFF2` | 否 | 否 | 否 | 超出边界且未对齐 |
| LC-10 | `0x100001E` | `0x1000000` | 是 | 否 | 否 | 首个对齐但超过客户端 `0xFFFFFF` 的密文值 |

### 6.1 重要更正

- `0xFFFFF`、`0x100000`、`0x100001` 都是**外层长度字段值**，不是所有都对应 16B 对齐的合法帧。
- 本地 parser 的 `0x100000` 是外层字段策略上限。
- 客户端 `0xFFFFFF` 是密文长度上限。
- 最大对齐外层值应是 `0x100000E`，不能直接把 `0x100000` 与 `0xFFFFFF` 比较。

## 7. 兼容性判断

### 7.1 是否影响现有 G3 结果

- G3 已执行的小向量、MAC、tag 截取、短帧和截断帧结果不受影响。
- TC-29 原有字段值测试不足以覆盖完整大帧兼容性；其“长度上限”结论需要按本报告分层重述。
- 现有 parser 不需要在本任务中扩大。若目标场景没有实际超过 `0x100000` 的帧，应保持现状并记录适用范围。

### 7.2 是否需要改变 parser

当前证据支持：

```text
保持 parser 0x100000，不修改。
记录：
  - 本地 parser 上限是独立策略；
  - 客户端静态密文约束更高；
  - 大帧 E2E 未验证；
  - 任何扩大必须另立变更与回归测试。
```

不支持：

- 直接把 parser 上限扩大到 `0xFFFFFF`；
- 直接把 parser 上限改成 `0x100000E`；
- 将本地模型结果称为原版运行时行为；
- 在没有目标使用场景和完整大帧测试时，仅为了数值一致而放宽限制。

## 8. TC-27 状态修订建议

Counter-boundary 静态审计已给出直接证据：

```text
expected=0xFFFFFFFF, incoming=0
=> reject
=> expected is written as 0
=> failure path sets state 4
```

因此 TC-27 不再是 `BLOCKED-INSUFFICIENT-SPEC`：

- 静态行为状态：`CONFIRMED-STATIC`；
- 测试状态建议：`PASS (STATIC BEHAVIOR RECORDED)`；
- 运行时状态：`UNRESOLVED / NOT-OBSERVED`；
- 原 G3 测试矩阵不得被覆盖；应新增登记或 delta。

## 9. 最终结论

本地 parser 的 `0x100000` 与冻结客户端密文约束之间的差异是真实的，但属于**不同字段层**的实现差异。它不影响当前小帧 G3 固定向量结论；是否影响目标构建的实际兼容性，取决于目标场景是否需要大于约 1MiB 的完整合法帧。该问题仍为独立残余风险，不自动提升 G3，也不改变 G4/G5 与实时互通 `NOT-OBSERVED`。

## 10. 交付物

- `CODOL_LENGTH_COMPATIBILITY_AUDIT_001.md`
- `CODOL_LENGTH_BOUNDARY_CASES_001.csv`
- `CODOL_G3_STATUS_RECONCILIATION_001.md`
- `SHA256SUMS_LENGTH_COMPATIBILITY_001.txt`
- `_data/length_compatibility_evidence.json`
- `_tools/length_compatibility_audit.py`