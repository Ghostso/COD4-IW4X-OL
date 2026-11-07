# E23 执行摘要

## 一句话结论

`0xA85AD0`、`0xA85BE0`、`0xA85640`、`0xA87830`、`0xA878A0` 是五个**以 VA（ImageBase=0x400000）记法**的普通 `.text` 函数（RVA 分别为 `0x685AD0`、`0x685BE0`、`0x685640`、`0x687830`、`0x6878A0`）；E-22 将其判为 `.data` BSS 虚拟尾部是**地址基准（VA/RVA）误用**，其中 0xA878A0/0xA87830/0xA85AD0 是缓冲区 Range/Advance + memcpy 辅助、0xA85640/0xA85BE0 是 thiscall 字段分派，`[edi+0x5F4]` 成功路径调用可归约为"协商对象（vtable `0xC5A31C`）的 slot+3 字节流提交"。

## 关键事实

1. 五个地址按 **VA** 口径全部落在 `.text`（`VA 0x00001000..0x007AD90B`），有真实磁盘字节、可线性反汇编；只有在按 **RVA** 口径解释时才会落入 `.data`（`VA 0x8F1000`，RawSize `0x49600`）的 BSS 虚拟尾部。
2. E-22 的机器可读中间产物与 E-21 自述均把这些值写作 **VA**（例如 `call 0xA85AD0`、`call 0xa878a0`），其"BSS 无字节"结论来自把 VA 当成 RVA 查询节区映射。
3. 按 VA 重算 rel32 得到的真实调用点：
   - `0xA85AD0`：`0x6AC168`（位于 `0x6AC0C0` 内，解析消息码）
   - `0xA85640`：`0x6AC22C`、`0x6A5CCA`（共 36 处）
   - `0xA85BE0`：`0x6AC2BC`、`0x6AC37B` 等（共 96 处）
   - `0xA87830`：125 处
   - `0xA878A0`：96 处（含 `0x6AAEF4`、`0x6AAF22`）
4. 函数语义（`.text`，非 BSS）：
   - `0xA878A0`（`0x6878A0`）：计算 span = `[ebp+0x10]+[ebp+0x1c]` 写回 `[ebp+0x14]`，越界则日志 `0x43A7C0`，否则 `memcpy`（`0xB49B40`）。
   - `0xA87830`（`0x687830`）：同类 Range 辅助，输出 24 字节结构。
   - `0xA85640`（`0x685640`）：thiscall 字段分派，`ret 8`，跳转 `.tvm0` 入口 `0xDF6F97C`。
   - `0xA85BE0`（`0x685BE0`）：thiscall 字段分派，`ret 4`，跳转 `.tvm0` 入口 `0xDF6F97C`。
   - `0xA85AD0`（`0x685AD0`）：`0xA878A0` 的簿记封装，`ret`（cdecl）。
5. 初始化来源：**TLS 回调为空**（数据目录 `AddressOfCallBacks` 指向的 `.rdata` 数组首元素为 0）、**`.rimp` 无任何目标地址引用**、无静态构造器写入——因为它们是普通 `.text` 代码，根本不需要"加载期写入 BSS"。
6. `[edi+0x5F4]`：字段由 `0x6AB9B3`/`0x6AB9E7` 写入（值 `0` 或构造对象指针），对象由 `0x6AB9D8`/`0x6AB9DA`（`call 0xA87BA0`）构造，vtable `0xC5A31C`；成功路径 `0x6AB14E` 取 slot+3 = `0xA87D50` 并用 4 个栈参数调用。

## 逐项裁定

| 地址 | VA → RVA | 所属节区 | 裁定 |
|---|---|---|---|
| 0xA85AD0 | 0x685AD0 | .text | CONFIRMED-CODE-FUNCTION（`0xA878A0` 封装） |
| 0xA85BE0 | 0x685BE0 | .text | CONFIRMED-CODE-FUNCTION（字段分派，`ret 4`） |
| 0xA85640 | 0x685640 | .text | CONFIRMED-CODE-FUNCTION（字段分派，`ret 8`） |
| 0xA87830 | 0x687830 | .text | CONFIRMED-CODE-FUNCTION（Range/memcpy，24B 输出） |
| 0xA878A0 | 0x6878A0 | .text | CONFIRMED-CODE-FUNCTION（Range 写回/memcpy） |

## `[edi+0x5F4]` 是否得到解释

是。`[edi+0x5F4]` 持有"协商/参数对象"指针，其 vtable 为 `0xC5A31C`；成功路径调用该对象 slot+3（`0xA87D50`），参数形如 `(this, buf, buf, len)`。该对象是 `.text` 对象，与五个目标**同属一族**（`0xA87xxx`/`0xAA8xxx`），**不再**是 E-22 所述"无磁盘字节的 BSS 虚表"。

## 被证伪/更正的关联假设

- **E-22「五地址位于 `.data` BSS 虚拟尾部」→ REFUTED（基准错误）**；正确为 `.text`。
- E-21「`0xA85AD0` 属 `.tvm0`」→ 仍为 REFUTED（正确为 `.text`）。
- E-22「I4 加权完备率 33.33%（I4 权重 96）」→ 与权威 XVAL-02 账本（I4=104）冲突，判为账目口径错误；正确为 32/104 = 30.77%。
- 新增 REFUTED：五个辅助函数**不是**"加载期被写入 BSS 的隐藏分派表"，而是被大量静态调用点（共 1+36+96+125+96 = 354 处）直接调用的普通函数。

## 阻塞项

- `0xA87830` 的 `[ebp+0x18]` 24 字节输出结构字段语义（部分见 `0x6B95C0` 写入 `0xffffffff`）。
- `0xA87D50` slot+3 的 4 个缓冲区参数语义与握手状态机的对应关系。
- 消息码 `0x81/0x83/0x84/0x85` 与出/入站方向的最终绑定。

## 下一步唯一建议

解析调用点 `0x6AB9D8` 的交叉引用，确定 `[edi+0x5F4]` 协商对象的创建时机与调用者，从而闭合握手状态机——这是唯一能在静态范围内进一步收敛的边界。
