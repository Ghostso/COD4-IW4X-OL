# ICH-059 — PRCL .tls Scheduler 函数级验证

## 判定

```text
ICH059_STATUS              = NOT_LOCATED
TLS_PRCL_ROLE              = UNKNOWN (data confirmed, scheduler function NOT found)
DECRYPTOR_CALLER           = NOT_LOCATED
SCHEDULER_FUNCTION         = NOT_LOCATED
TABLE_BUILDER              = NOT_LOCATED
ENGINE_DISPATCHER          = NOT_LOCATED
PRCL_TO_ENGINE             = UNKNOWN
NEXT_TARGET                = FREEZE_PRCL_STATIC_ANALYSIS
```

## 分析结果

### Agent 1-3: API 引用精确 RVA

| API | .tls RVA | VA |
|---|---|---|
| VirtualAlloc ref1 | 0xB045D2 | 0x10B045D2 |
| VirtualAlloc ref2 | 0xB04B6E | 0x10B04B6E |
| VirtualAlloc ref3 | 0xB05A74 | 0x10B05A74 |
| VirtualProtect ref1 | 0xB04BE8 | 0x10B04BE8 |
| VirtualProtect ref2 | 0xB04E7E | 0x10B04E7E |
| VirtualProtect ref3 | 0xB05B94 | 0x10B05B94 |
| NtProtectVirtualMemory | 0xB07080 | 0x10B07080 |

### Agent 4: API 引用上下文分析 — 关键发现

**所有 .tls 中的 API 名称引用都是 IMPORT NAME TABLE (INT) 条目。**

证据：
- VirtualAlloc 周围：VirtualFreeEx, Module32FirstW（标准 API 名列表）
- VirtualProtect 周围：GetSystemInfo, ReleaseMutex
- NtProtectVirtualMemory 周围：NtWriteVirtualMemory, VerSet
- 格式：hint(2 bytes) + null-terminated string + padding

**这些不是代码调用 API 的位置。是 dynamic import table 的 name entries。**

### Agent 9-12: Engine Gap 地址搜索

0x00CA0000 在 .tls 中出现 90 次，分布在 0xF82B03..0x19A4797（~10MB）。
全部散布在 VM bytecode/数据中（与 ICH-046 一致），不构成 dispatch descriptor。

### Agent 20: .tls = scheduler 假设证伪

| 支持 | 反对 |
|---|---|
| 15.5MB 异常大 | API 引用是 INT 条目，非代码调用 |
| 可执行 (ICH-040) | 90 个 Engine ref 散布在 VM 数据中 |
| 包含 Anchor A | 无 dispatch loop pattern |
| 包含 import table | 无 Engine Gap 地址计算代码 |
| | 无 96-table 构建代码 |
| | 无 indirect call 密集区域 |

### Agent 21: decryptor + scheduler 模型独立证伪

PRCL 控制函数可能位于：
a) .tls 可执行代码部分（未找到具体函数）
b) .tvm0 自身中（自解压/自包含）
c) ordinal 1 入口直接执行（无独立 scheduler）
d) 运行时动态生成

在不使用 debugger 或完整逆向 .tvm0 加密的前提下，无法从静态分析中定位。

## PRCL 三轮总结 (ICH-057+058+059)

| 搜索区域 | 搜索内容 | 结果 |
|---|---|---|
| .text (7.2MB) | .tvm0 地址引用 | 0 hits → interpreter 不在 .text |
| .tls (15.5MB) | API 引用、Engine 常量、dispatch loop | API = INT entries; Engine refs = VM data noise |
| .tvm0 (32MB) | XOR 加密的 Engine code | 非简单 XOR，复杂加密 |
| .tls Anchor A | 0x00E83B00 孤立引用 | 确认存在，无 dispatch context |
| .tls import table | VirtualAlloc/Protect refs | INT entries，非代码调用 |

**结论：PRCL 静态分析已到达边界。**

在不使用 debugger、不解密 .tvm0、不做全地址空间扫描的前提下，
无法定位 PRCL 的具体控制函数（decryptor / scheduler / table builder / dispatcher）。

## Hard Stop 触发

按任务要求："如果最后仍然只是 VirtualAlloc refs = 3, VirtualProtect refs = 3... 但没有任何 caller → Engine Gap → table → indirect call，那么就立即停止 PRCL 静态搜索。"

PRCL 静态分析正式冻结。

## 对后续路线的建议

从 ICH-057~059 三轮 PRCL 分析得出的结论：

**Engine 的 3.08MB 完整 native code 存在且可执行，但被 PRCL 保护层完全控制。**

在不恢复 PRCL（解密算法 + 调度逻辑）的前提下：
- 无法触发 Resource Event
- 无法执行 Game Init
- 无法到达 Frontend

PRCL 恢复需要：
1. .tvm0 解密算法逆向（从 ciphertext 猜 cipher，信息不足）
2. 或 debugger 动态跟踪（已确认不可用）
3. 或 VM bytecode interpreter 恢复（可能不存在传统 interpreter）

## 输出

- ICH059_DECISION.md
