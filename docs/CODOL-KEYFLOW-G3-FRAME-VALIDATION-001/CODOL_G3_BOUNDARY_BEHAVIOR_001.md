# CODOL G3 边界行为记录（001）

> 任务：`CODOL-KEYFLOW-G3-FRAME-VALIDATION-001`
> 本文件记录本地参考夹具的返回值/拒绝位置/状态一致性；不把夹具行为直接归因于原版客户端。

## 1. 帧长度边界

### 1.1 固定向量往返（TC-16）

| payload 长度 | 固定编码帧总长 | 结果 |
|---:|---:|---|
| 0 | 50 | accept，往返一致 |
| 1 | 50 | accept，往返一致 |
| 3 | 50 | accept，往返一致 |
| 7 | 50 | accept，往返一致 |
| 15 | 66 | accept，往返一致 |
| 16 | 66 | accept，往返一致 |
| 17 | 66 | accept，往返一致 |
| 63 | 114 | accept，往返一致 |
| 64 | 114 | accept，往返一致 |
| 65 | 114 | accept，往返一致 |
| 255 | 306 | accept，往返一致 |

计算关系：`frame_len = 34 + ceil((5 + payload_len)/16)*16`。空 payload 仍需一个 16B 密文分组，因此最小合法 0x86 帧为 **50B**。

### 1.2 总长扫描（TC-32）

| 总长范围 | 本地直接解码结果 |
|---|---|
| 0–3B | reject（`min-total-50`；不足以读头部） |
| 4B | 解析层可分类为 keepalive；作为 0x85 帧解码 reject |
| 5–33B | reject（`min-total-50`） |
| 34–49B | reject（`min-total-50`） |
| 50B（空 payload 0x85/0x86 固定向量） | accept |

TC-32 的 0x85 短帧扫描排除了 4B keepalive 语义，后者单列在 TC-28。

## 2. 长度字段与缓冲不一致（TC-29/TC-30）

| 场景 | 输入 | 本地 parser | 直接解码/判定 |
|---|---|---|---|
| 长度高于设定上限 | `len=0x100001` + 32B 数据 | 不消费，保留 36B | parser 的 1MiB 上限拒绝；冻结客户端 `>=0xFFFFFF` 不在此处拒绝，构成参考差异 |
| 位于客户端上限边缘 | `len=0xFFFFFF` + 32B 数据 | 不消费，保留 36B | 拒绝；与客户端静态 `jge 0xFFFFFF` 一致 |
| 远高于上限 | `len=0xFFFFFFFF` + 32B 数据 | 不消费，保留 36B | 拒绝 |
| 声明 0x100，实际 4B | 不完整帧 | 不消费，保留 6B | 直接解码 reject |
| 声明 0x100，实际 16B | 不完整帧 | 不消费，保留 18B | 直接解码 reject |
| 声明 0x100，实际 33B | 不完整帧 | 不消费，保留 35B | 直接解码 reject |
| 声明小于实际 | 声明 `len-5`、4、5 等 | 切出短候选帧，余量保留 | 候选因长度字段不匹配拒绝 |

本文件所称“拒绝”仅指本地测试夹具不接受为完整帧；没有证明原版客户端一定仅丢弃而不执行其他状态迁移。

## 3. 密文与标签边界（TC-21/TC-23/TC-31）

| 条件 | 输入 | 拒绝位置 | 结果 |
|---|---|---|---|
| 密文为空 | `ct_len=0` | `min-total-50` | reject |
| 密文 1B | `ct_len=1` | `min-total-50` | reject |
| 密文 15B | `ct_len=15` | `min-total-50` | reject |
| 密文 17B | `ct_len=17` | `ct-align`（17%16 != 0） | reject |
| tag 8B | 与协议截断一致 | 无 | accept |
| tag 9B | 额外 1B 改写了 HMAC 覆盖终点 | `hmac` | reject |
| tag 20B | 使用完整 HMAC-SHA1 输出 | `hmac` | reject |
| tag 0/1/4/7B | 短 tag | `min-total-50` | reject |

**拒绝阶段优先级**：本地夹具先检查 `len<50`，再检查 `len` 字段、固定标记、HMAC、密文对齐、明文声明长度和 payload 边界。因此一些“短 tag”输入在进入 HMAC 比较前就被最小帧长拒绝。

## 4. MAC 覆盖边界（TC-19/TC-20/TC-22）

| 逻辑条件 | 结果 |
|---|---|
| `HMAC-SHA1(key, frame[:-8])[:8] == frame[-8:]` | accept |
| 标签字节被翻转且不重算 | reject（`hmac`） |
| 覆盖区内字节被翻转且不重算 | reject（`hmac` 或更早的 `marker` 检查） |
| 覆盖区内字节被翻转后重算 tag | HMAC 可 pass；完整解码是否 accept 取决于字段语义 |
| 将 `frame[:-9]` 作为覆盖范围 | 不匹配 |
| 将完整 `frame`（含 tag）作为覆盖范围 | 不匹配 |

本地边界检查没有发生越界读写。对原版客户端的失败处置（断开、丢弃、幂等性）没有在本任务中验证。

## 5. 序列号边界（TC-24…TC-27）

使用严格相等模型（expected 初始值 -> 处理帧）：

| 用例 | expected 初值 | 输入 seq | 结果 | expected 终值 | 状态一致性 |
|---|---:|---:|---|---:|---|
| TC-24a | 1 | 1 | accept | 2 | 是 |
| TC-24b | 2 | 2 | accept | 3 | 是 |
| TC-25 | 2 | 1 | reject | 2 | 是 |
| TC-26a | 2 | 3 | reject | 2 | 是 |
| TC-26b | 2 | 4 | reject | 2 | 是 |
| TC-27 候选 A | 0xFFFFFFFF | 0 | reject（严格相等） | 0xFFFFFFFF | 是（模型状态不变） |
| TC-27 候选 B | 0xFFFFFFFF | 0 | accept（模 2^32 回绕） | 1 | 候选行为，未被选中 |

TC-27 不产生 PASS/FAIL 结论，只记录候选语义；冻结证据不能选定接纳或拒绝规则。

## 6. 非法输入的返回/异常分类

本地夹具用结构化异常/拒绝阶段记录，不使用未定义行为：

| 阶段标签 | 触发条件 |
|---|---|
| `min-total-50` | 总长小于 50B，或密文为 0B |
| `length` | `u32len + 4 != len(frame)` |
| `marker` | `frame[4:6] != AB 85` |
| `hmac` | 截断 HMAC 不匹配 |
| `ct-align` | 密文为空或非 16B 对齐 |
| `declared` | 明文声明的长度越界或消息类型不允许 0 长度 |
| `payload-bounds` | payload 超出明文缓冲范围 |

所有扫描用例均记录 `out_of_bounds = false`；未观察到崩溃或序列号状态污染。

## 7. 边界结论

- 帧长下界为 **50B**（对至少一个 AES 分组、0x85 固定头、8B tag 的组合）。
- 4B keepalive 是独立分支，不属于 0x85 短帧。
- `len` 字段为 little-endian 且等于整帧长度减 4。
- MAC 覆盖 `frame[:-8]`，tag 为该 HMAC 的前 8B。
- 本地 parser 与冻结客户端在长度上限存在已知差异（1MiB vs 约16MiB）；该差异已单列，不影响本轮其他固定向量的逐字节结果。