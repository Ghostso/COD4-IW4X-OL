# ICH-055 — Game Init / Frontend Entry Archaeology

## 判定

```text
ICH055_STATUS           = NOT_LOCATED
GAME_INIT_ENTRY         = NOT_LOCATED
FRONTEND_ENTRY          = NOT_LOCATED
RESOURCE_DEPENDENCY     = STRONG_CANDIDATE
NEXT_TARGET             = STOP
```

## 证据汇总

### 已有发现（EXE / Engine side）

| 发现 | 证据来源 | 分类 |
|---|---|---|
| 22 Scaleform C++ mangled exports | ICH-006/007 | CANDIDATE (UI layer, ENTRY_INDEPENDENT) |
| settings_c.zip.iw4 push ref | CORE-007 (0x00454C4F) | CANDIDATE (obfuscated stream) |
| main\%s push ref | CORE-007 (0x00639B7C) | CANDIDATE (obfuscated stream) |
| config_mp string | CORE-007 (0x009BCFE0) | CANDIDATE (no code ref) |
| IW4 lineage: Com_Init→FS_Init→DB_Init→CL_Init | ICH-003/006/013 | CANDIDATE only (CODOL analog not found) |
| BOOT_08_GAME_INIT | CORE-010 | UNKNOWN (no direct address/call/structure) |
| No plain Game/Engine Init function reachable | EX-011 | CONFIRMED_ABSENCE |

### 96-entry dispatch table 潜在 Game Init clusters

| Cluster | Address Range | Slots | Pattern | Potential Role |
|---|---|---|---|---|
| 2 | 0x9BA5B0..0x9C0010 | ~6 | complex | Processing/Init |
| 5 | 0x9C37C0..0x9C3930 | 6 | large_frame | Major Init |
| 10 | 0x9CD630..0x9DB5F0 | ~4 | large_frame | Major Subsystem |

这三个 cluster 可能包含 Game Init / Dvar / Renderer / Sound 初始化逻辑，
但它们的函数语义只有 access pattern 和 frame size 分类，没有字符串引用或调用关系确认。

### 为什么 Game Init 不可达

1. **EXE plain code**: Game Init 消费代码（引用 config_mp, settings 等）位于 VM-protected sections。唯一的 push 引用在 obfuscated streams 中，无法建立完整 dataflow。

2. **Engine gap**: 96-entry dispatch table 中的 Game Init 候选函数（Cluster 2/5/10）的 caller 同样是 VM dispatch mechanism（ICH-053 确认）。没有 native caller。

3. **No runtime evidence**: 在 Local RM 环境下（30s+ stable），Engine 没有执行任何 Game Init / Dvar / Renderer / Sound 初始化活动。

4. **Scaleform exports**: 这 22 个函数是 UI layer，ENTRY_INDEPENDENT（不依赖 entry）。它们不能作为 Game Init 的入口。

5. **IW4 lineage**: Com_Init → FS_Init → DB_Init → CL_Init 的 IW4 启动链在 CODOL 中只有谱系类比（CANDIDATE），没有建立函数等价。

### RESOURCE_DEPENDENCY = STRONG_CANDIDATE

Game Init 是否必然依赖 Resource Trigger？

**STRONG_CANDIDATE**：
- IW4 lineage 中，Com_Init 依赖 FS_Init 和 DB_Init（即 FF/Zone/Asset）
- CODOL 的 Engine gap 包含完整的 Zone/FF/Asset/Dvar/Renderer/Sound 代码（ICH-025）
- 但这些代码全部在 96-entry dispatch table 后面
- Dispatch table 的激活由 VM dispatch 控制
- VM dispatch 的 Resource Trigger 已确认不可从外部触发（ICH-054）

因此：Game Init **很可能**依赖 Resource Trigger，因为 IW4 谱系的初始化链
是 Resource → Zone → Asset → Dvar → Renderer → Game → Frontend。
但没有直接的函数级调用证据来升级到 CONFIRMED。

## Hard Stop

满足 Hard Stop 条件：无法将 Engine function 与 Game Init / Frontend 建立
可靠关系超过 CANDIDATE。

不扩大范围。

## 输出

- ICH055_DECISION.md
