# ICH-058 — .tvm0 → Engine Gap 解密器 + Dispatch Scheduler 定位

## 判定

```text
ICH058_STATUS                     = PARTIAL
DECRYPTOR_LOCATED                 = UNKNOWN (not simple XOR, complex encryption)
SCHEDULER_LOCATED                 = CANDIDATE (.tls contains PRCL evidence)
INDIRECT_CALL_DESCRIPTOR_LOCATED  = NOT_LOCATED
RESOURCE_TRIGGER_CONTROL_LOCATED  = NOT_LOCATED
NEXT_TARGET                       = STOP_OR_USER_DECISION
```

## 术语更新

从本轮开始，项目内部术语从 "VM" 改为 **Protected Runtime Control Layer (PRCL)**:

```
PRCL-Decryption: .tvm0 → Engine Gap 解密
PRCL-Dispatch:   96-entry table + indirect call
PRCL-State:      Root Object + subsystem objects
PRCL-Trigger:    Resource Event / Game Init 激活
```

## Agent 01-04: .tvm0 → Engine Gap 对照

搜索 .tvm0 (32MB) 中的 Engine code pattern：

| 方法 | 结果 |
|---|---|
| 直接搜索 `mov eax,0x9B9C00` (5 bytes) | 0 hits |
| XOR key 0x01, 0x10, 0x20, 0x42, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xCC, 0xDD, 0xEE, 0xFF, 0x2A, 0x5A | 全部 0 hits |

**结论：.tvm0 中的 Engine code 不是简单 XOR 加密。**

可能使用：多字节 XOR key、流密码、分块加密、压缩+加密、或 .tvm0 不直接包含 Engine code。

## Agent 05: Memory API 搜索

在 Base.dll 全文件中搜索 VirtualAlloc / VirtualProtect / NtProtectVirtualMemory：

| API | .rdata | .tls | 其他 |
|---|---|---|---|
| VirtualAlloc | 1 | 3 | 2 (import) |
| VirtualProtect | 1 | 3 | 3 (import) |
| NtProtectVirtualMemory | 0 | 1 | 3 (import) |

**关键发现：.tls 段中出现全部三个 Memory API 的字符串引用。**

这支持 .tls = PRCL 假设：
- .tls 包含与内存保护/分配相关的控制数据
- .tls 中有 3 处 VirtualAlloc + 3 处 VirtualProtect + 1 处 NtProtectVirtualMemory
- 这些可能是 PRCL 解密 Engine Gap 时使用的 API 引用

## PRCL 模型更新

```
Base.dll ordinal 1
    │
    ▼
PRCL (Protected Runtime Control Layer)
    │
    ├── .tls: 15.5MB 可执行区域
    │   ├── PRCL-Decryption 控制 (VirtualAlloc/VirtualProtect refs)
    │   ├── PRCL-Dispatch scheduler
    │   └── PRCL-State management
    │
    ├── .tvm0: 32MB 加密数据
    │   ├── Engine native code (encrypted, not simple XOR)
    │   └── Control data (dispatch metadata)
    │
    ├── 解密引擎 (位置 UNKNOWN, 可能是 .tls 中的代码)
    │   └── .tvm0 → Engine Gap (0x00994000..0x00CA789A)
    │
    └── Dispatch scheduler
        ├── 96-entry table 构建
        ├── 0x00CA0000 dispatch
        └── 后续 Engine 函数 dispatch (当前阻塞)
```

## PRCL-Decryption 评估

.tvm0 中 Engine code 的加密不是简单 XOR。
需要进一步分析才能确定加密算法。

**当前状态：UNKNOWN（未能定位解密 routine）**

解密 routine 可能：
- 在 .tls 段的可执行代码中
- 在 Base.dll .text 中但使用间接寻址
- 在 .tvm0 自身的前几个 block 中（自解压）

## PRCL-Dispatch 评估

.tls 包含 PRCL 控制数据的证据：
- 3 处 VirtualAlloc 引用
- 3 处 VirtualProtect 引用
- 1 处 NtProtectVirtualMemory 引用
- 15.5MB 可执行区域（远超正常 TLS 大小）
- Anchor A (0x00E83B00 ref) 在 .tls 中

**当前状态：CANDIDATE（有间接证据支持，未直接确认 scheduler 代码）**

## PRCL-Trigger 评估

Resource Trigger 由 PRCL-Dispatch 控制 gorą。
在 PRCL-Dispatch 未定位的情况下，PRCL-Trigger 也不可定位。

**当前状态：NOT_LOCATED**

## Hard Stop 评估

ICH-058 的 A/B/C/D 成功等级：

| 等级 | 目标 | 结果 |
|---|---|---|
| A | decryptor + scheduler | ✗ |
| B | decryptor only | ✗ |
| C | scheduler only | PARTIAL (.tls PRCL 证据) |
| D | 都找不到 | ✗ (有 .tls 线索) |

实际结果介于 C 和 D 之间：找到了 .tls = PRCL 的间接证据（Memory API 引用），但没有直接定位 scheduler 代码或解密算法。

## 建议

当前项目已经到了 PRCL 层的边缘。
继续推进需要：

1. **深入分析 .tls 段**（15.5MB 可执行区域中定位 scheduler loop）
2. **逆向 .tvm0 加密算法**（从解密后的 Engine code 反推）
3. **动态观察 .tls 执行**（需要新的非-debugger instrumentation）

这三个方向都需要显著的技术投入，且结果不确定。

## 输出

- ICH058_DECISION.md
