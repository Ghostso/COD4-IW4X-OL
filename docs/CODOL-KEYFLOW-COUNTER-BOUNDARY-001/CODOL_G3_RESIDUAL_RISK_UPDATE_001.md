# G3 残余风险更新（001）

> 任务：`CODOL-KEYFLOW-COUNTER-BOUNDARY-001`
> 输入：冻结的 G3 结果、差异报告、边界行为报告、决策文件、原始测试脚本与执行日志。
> 历史文件只读；本文件只做增量更正，不覆盖 G3 原始记录。

## 1. 更新摘要

| 事项 | 新状态 | 对 G3 的影响 |
|---|---|---|
| TC-27 回绕 | `CONFIRMED-STATIC` | 原 `BLOCKED-INSUFFICIENT-SPEC` 可由静态行为记录关闭 |
| 序列号失败状态模型 | `CONFLICTING-EVIDENCE` | 原模型“失败时 expected 不变”被修正 |
| 长度上限层次差异 | `CONFIRMED-STATIC` | 发现外层 u32len 与客户端密文长度上限处于不同层 |
| 大帧实际兼容影响 | `UNRESOLVED` | 未执行大规模/大帧验证，不撤销小帧固定向量结果 |
| 运行时互通 | `NOT-OBSERVED` | 不因本任务改变 |

## 2. 序列号模型更正

原 G3 边界报告中采用：

```text
if incoming != expected:
    reject
    expected unchanged
```

冻结客户端接收函数 `0x00AAAE70` 的真实静态顺序为：

```text
old = [obj+0x5D0]
[obj+0x5D0] = (old + 1) mod 2^32
if incoming != old:
    reject
```

这改变以下失败后状态：

| 用例 | 接受/拒绝 | expected 终值（客户端静态） | 原 G3 模型 |
|---|---|---|---|
| 正常 seq=expected | accept | expected+1 | 相同 |
| 重复 seq=expected-1 | reject | expected+1 | expected 不变 |
| 跳号 seq>expected | reject | expected+1 | expected 不变 |
| expected=0xFFFFFFFF, seq=0 | reject | 0 | 原为 blocked/候选 |

此外，接收失败路径调用 `0x00AAA770`，在 `0x00AAA791` 写 `[obj+0xC8]=4`；调度器对状态 4 提前返回。因此不能仅从“计数器已变成 0”推断同一连接会接受下一帧。

建议将原 G3 序列号模型标记为 **superseded**，未来离线测试采用：

```text
post-increment-before-compare
```

但仍不得将此静态模型包装成运行时客户端行为。

## 3. 长度边界层次更正

### 3.1 原比较中的层次混淆

G3 差异报告曾把以下两者作为同一上限比较：

```text
本地 parser: ln > 0x100000
客户端:      cmp ..., 0xFFFFFF
```

重新做数据流后：

- 本地 parser 的 `0x100000` 是 **外层 `u32len` 字段上限**：
  ```text
  ln = little-endian u32 at buffer[off:off+4]
  if ln > 0x100000: stop consuming
  ```
- 客户端 `0xAAAF80` 的 `cmp ecx,0xFFFFFF` 中，`ecx` 是：
  ```text
  tag_address - ciphertext_start = ciphertext byte length
  ```
  这是 **密文长度上限**，不是外层 `u32len` 的直接比较。

所以两者不是同一个数值层的上限，不能只写：

```text
local 0x100000  vs  client 0xFFFFFF
```

### 3.2 转换后的边界

由已验证的帧关系：

```text
ciphertext_len = total_frame - 34
u32len          = total_frame - 4 = ciphertext_len + 30
```

客户端密文检查要求：

```text
ciphertext_len % 16 == 0
ciphertext_len < 0xFFFFFF
```

最大 16B 对齐且符合小于条件的密文长度：

```text
0xFFFFF0
```

对应的外层 `u32len` 最大值为：

```text
0xFFFFF0 + 0x1E = 0x100000E
```

对应总帧长度为：

```text
0x1000012
```

因此更准确的层间差异是：

```text
本地 parser：外层 u32len 最大可接受 0x100000
冻结客户端：由密文检查转换得到的外层 u32len 约 0x100000E
差异区间：0x100001 .. 0x100000E（按 16B 对齐的有效帧再取子集）
```

### 3.3 影响范围

- 小帧固定向量（G3 的 TC-16…TC-28、TC-30…TC-32）不受该数值差异影响。
- 现有 TC-29 只测了字段值和本地 parser，没有构造该区间中的完整有效大帧。
- 因此不能把本地 parser 上限扩大为 `0xFFFFFF`，也不能把它直接改成 `0x100000E`；需要独立、安全、可审计的验证。
- 大规模内存分配和超大输入不在本任务执行范围内，状态为 `UNRESOLVED`。

完整层间对照见：

- `CODOL_FRAME_LENGTH_BOUNDARY_AUDIT_001.csv`
- `_data/counter_boundary_static_evidence.json`

## 4. 对原 G3 结论的增量影响

### 仍然成立

- 固定布局、MAC 覆盖、8B tag 截取和抓包重编码的本地小向量结果不受影响。
- 本地夹具对短帧、截断帧、长度不一致和密文非 16B 倍数的拒绝结果不受影响。
- TC-27 现在有直接静态行为证据，可以从“规范不足”升级为“静态行为已记录”。

### 需要修正

- G3 原序列号模型必须改为先递增、后比较。
- “失败时 expected 不变”应从任何新结论中删除；历史报告保留原文，但引用时须注明本更新。
- 长度上限差异必须分两层描述：外层 `u32len` vs 密文长度 `ecx`。
- 不能把本地 parser 的 `0x100000` 直接描述成与客户端 `0xFFFFFF` 同一层的边界。

### 仍不能升级

- 不能宣布 G3 无条件通过。
- 不能宣布运行时回绕行为已验证。
- 不能宣布原版客户端在失败后一定断开、丢弃或保持哪种连接状态。
- 不能宣布大帧兼容性已验证。
- 实时互通仍为 **NOT-OBSERVED**。

## 5. 风险登记

| 风险 | 分类 | 当前处置 |
|---|---|---|
| 序列号失败路径会先推进 expected | `CONFIRMED-STATIC` | 更新模型；不要沿用旧假设 |
| FFFFFFFF -> 0 的同连接后续行为 | `UNRESOLVED` | 保留待运行时或更完整状态机证据 |
| HMAC 失败前的 expected 推进 | `CONFIRMED-STATIC` | 记录；错误处置仍需运行时确认 |
| 本地 parser 1MiB 上限与客户端密文上限层差异 | `CONFIRMED-STATIC` | 作为独立兼容性缺口登记；不修改冻结证据 |
| 大帧分配/读取策略 | `UNRESOLVED` | 不做大规模分配；等待安全测试环境 |
| 原始 G3 序列号模型 | `CONFLICTING-EVIDENCE` | 由本更新取代，不删除原始文件 |

## 6. 结论

本更新解决了 TC-27 的静态回绕问题，但发现并修正了原 G3 序列号状态模型；同时确认长度上限差异属于不同字段层的实现差异，而不是可安全合并的同一阈值。

建议 G3 保持：

```text
G3 = PARTIAL PASS (CONDITIONAL)
TC-27 static behavior: now confirmed
Sequence failure-state model: corrected
Large-frame parser compatibility: separate open gap
Runtime interoperability: NOT-OBSERVED
```

本任务完成**不**代表 G3 自动通过，也不改变 G4/G5 和 `NOT-OBSERVED` 状态。