# F1 — 客户端 RVA 0xA2E50 调用者追踪

> 客户端样本 SHA-256：`353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`  
> 静态恢复镜像 SHA-256：`24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`  
> ImageBase：`0x400000`；本文地址基准：`0xA2E50`/`0xA2D90` 为映像 RVA，函数内部 E8 目标为 VA（VA - ImageBase = RVA）。

> 结论等级：指令事实 VERIFIED；调用者闭环 BLOCKED。

## 1. 确认的函数边界与语义

函数：RVA `0xA2E50`–`0xA2FDE`（下一条 `int3` 填充至 `0xA2FFA`）。关键读序（VERIFIED）：

```asm
004a2e67  mov ecx,[esi+0x18]
004a2e6a  mov eax,[esi+0x1c]
004a2e6d  add ecx,[esi+0x14]
004a2e7a  cmp edi,ecx
004a2e87  call 0x5ac1d0       ; 读取 4 字节
004a2ec0  call 0x5ac1d0       ; 读取 2 字节 length
004a2ecf  mov eax,0x3fc
004a2edd  cmp di,ax
004a2f02  call 0x5acb00       ; 复制 payload
004a2f2a  cmp [edi+0x4014c],ebx
004a2f73  lea ecx,[esi+edi+0x40154]
004a2fc6  call 0x631ce0
```

可确认字段序列：**long(4) + short(2) + payload[length]（长度上限 0x3FC）**；读取核心目标 `0x5AC1D0` 是 VA 形式，对应 RVA `0x1AC1D0`（见 F4）。最终把内容写入按 `EBX & 0xFF` 选取的约 `0x400` 字节槽。

## 2. 调用者搜索结果

搜索范围：整个恢复镜像全部节；方法：

1. 对 VA `0x4A2E50` 与 RVA `0xA2E50` 两种形式搜索绝对 dword 指针；
2. 对全部节扫描 `E8/E9 rel32`，逐条计算目标；
3. 对跳转表/间接跳转候选检查。

结果：

| 搜索 | 结果 | 等级 |
|---|---|---|
| 绝对 dword `0x4A2E50` | 0 命中 | VERIFIED（当前镜像） |
| `.text` 内 E8/E9 → `0x4A2E50` | 0 命中 | VERIFIED（当前镜像） |
| 全镜像 E8/E9 → `0x4A2E50` | 1 命中：`.tvm0` RVA `0xD9D940F`，文件偏移 `0x9C320F` | 不能认定为调用 |
| 跳转表目标 | 未发现指向 `0x4A2E50` 的表项 | BLOCKED（未穷尽所有间接形式） |

### 2.1 `.tvm0` 命中为何不能算调用者

```text
0DDD940D  fd                 std
0DDD940F  e8 ...             ; 字节上构成 E8，但前序不是函数边界
0DDD9414  jmp 0xDD6F483
```

该位置处于 `.tvm0` 数据/编码区，反汇编没有连续可验证的函数序言、参数准备或 `0xA2E50` 的 `ECX` 对象设置；判定为**未对齐数据命中**。因此不满足“可复现调用者”。

## 3. 结论

**F1：没有找到可复现的 RVA `0xA2E50` 调用者。** 该函数的字段形状可验证，但“谁用 opcode 0x02 调它”在静态恢复镜像中无法闭合。

- 读序与边界：`VERIFIED`
- 无 `.text` 直接调用/绝对指针：`VERIFIED`（限于本镜像）
- 调用者关系：`BLOCKED`
- 运行时行为：`NOT-OBSERVED`
