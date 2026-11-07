# CODOL STANDALONE-CORE-001
## EXE Self-Sufficient Game Startup Reconstruction

**研究对象**：`codoMP_client_shipRetail.exe`
**范围**：仅 EXE 自身启动/外部边界；不进入 DLL 内部，不进入 `.tvm0`。
**最终分级**：`EXE_CUSTOM_BOOTSTRAP_CONFIRMED`、`TVM0_BOUNDARY`、`OBSERVER_NO_DIVERGENCE`

## 1. 核心判断

不要继续问“为什么启动失败”。
真正的问题只有一个：

```text
EXE 自身是否拥有完整的 GAME START -> GAME INIT -> RUNTIME -> MAIN LOOP 路径？
```

当前证据支持的最强结论是：

```text
CONFIRMED : EXE Entry -> Base.dll ordinal_1
CONFIRMED : Base entry -> Base+0x149C -> Base+0x1AA13B0 (.tvm0 boundary)
STRONG    : 0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0
CANDIDATE : Network / STUN init, multi-subsystem bootstrap dispatcher
UNKNOWN   : Game Init, Renderer, Filesystem, Main Loop
BLOCKER   : WIN_IIPS_INIT_ERROR / 8189FEC 是当前首个已验证硬阻塞
NOT A HARD DEP : WeGame / TCLS Client.exe / TCLS.dll / TCLS shared memory
```

## 2. Confirmed

### EXE -> Base.dll

- `0xE5DC690` -> `0x0E9DC665` -> `codoMP_client_shipRetailBase.dll` `ordinal_1`
- 证据：入口 `call dword ptr [0x0E9DC665]`；`0x0E9DC635` 为 custom binding 描述符；PE 导出表确认 `Base+0x1D6582C` 为 `ordinal_1`。
- 结论：这是当前唯一已确认的明确 Base 边界。

### Base / VM boundary

- `Base+0x149C` -> `jmp Base+0x1AA13B0`
- 证据：动态命中与静态边界共同支持。
- 结论：EXE/Base 侧确实存在 VM boundary；`.tvm0` 内部未分析。

### Minimal direct-launch 可达性

- 直接启动时：
  - WeGame：未启动
  - TCLS Client.exe：未启动
  - TCLS.dll：未加载
  - TCLS shared memory：未出现
- 结论：EXE 可进入 native bootstrap；腾讯登录器不是当前已证实的前置硬依赖。

## 3. Strong Evidence

### 0x77F580 argv/context gate

- 静态证据显示其读取 argv；`-q` / `-qa` 可绕过 `WIN_NO_TCLS`。
- 已观察到直接调用链片段：
  - `0x77F8B3 -> 0x4FD9B0`
  - `0x4FDA03 -> 0x4FCEE0`
  - `0x4FD287 -> 0x808650`
  - `0x808658 -> 0x7E98F0`
  - `0x7E9913 -> 0x6212C0`
  - `0x621AC6 -> 0x6212C0` 内部递归
- 结论：plain `.text` 的 bootstrap/network dispatcher 链已恢复；尚不能证明完整 Game Init 到 Main Loop。

### 0x6212C0 mode init

- 读取：
  - `0x849413B`
  - `0x849B500`
- 字符串：
  - `stun1-tub.codol.qq.com`
  - `stun.us.demonware.net`
- 结论：STRONG evidence for network/STUN mode init；不等于完整 runtime。

## 4. Candidates

- `0x4FD9B0`：bootstrap dispatcher candidate
- `0x4FCEE0`：multi-subsystem init candidate
- `0x808650`：subsystem dispatcher candidate
- `0x7E98F0`：network subsystem init candidate
- Main Loop / Renderer / Filesystem / Game Init：均为 CANDIDATE 或 UNKNOWN
- 动态加载：
  - 静态扫描未发现 EXE plain-text 内的 confirmed `LoadLibrary*` / `GetProcAddress` call site
  - 结论：`DYNAMIC_MODULE_TARGET_UNKNOWN`

## 5. Unresolved

- `0x77F580` 的 EXE plain-text 上游 caller
- `0x6212C0` 之后的 confirmed next native stage
- Game Init / Renderer / FS / Main Loop 的完整 EXE-native path
- `8189FEC` 的精确来源
- `WIN_IIPS_INIT_ERROR` 的完整 error dispatcher
- 大量 global reader/writer 语义
- `Base+0x149C` / `Base+0x1AA13B0` 之后的完整 DLL-side 执行链
- `.tvm0` 内部结构

## 6. Not Analyzed

- `Base.dll` internals
- `iips.dll` internals
- TenProxy / TenRpcs / GameRpcs / tcj / GbSpy / policyprobe / tersafe / ACE-DRV32 / libcef internals
- `.tvm0` internals
- 任何 DLL 的内部实现

## 7. EXE Runtime Architecture

当前最高置信度架构：

```text
ENTRY
  -> EXE Entry 0xE5DC690
  -> Base ordinal_1 0x1D6582C
  -> Base entry 0x149C
  -> VM boundary Base+0x1AA13B0
  -> 0x77F580 bootstrap/argv gate (STRONG)
  -> 0x4FD9B0 / 0x4FCEE0 bootstrap dispatcher (CANDIDATE)
  -> 0x808650 / 0x7E98F0 subsystem dispatcher (CANDIDATE)
  -> 0x6212C0 STUN/network mode init (CANDIDATE)
  -> IIPS init -> 8189FEC -> BLOCKED
```

未达到：
- Renderer Init
- Resource / Filesystem Init
- Game Initialization
- Main Loop

最终状态机：

```text
S0  Process Created
S1  EXE Entry reached
S2  Base ordinal_1 reached
S3  Base/VM boundary reached
S4  Bootstrap dispatcher reached
S5  Network/STUN candidate reached
S6  IIPS init / 8189FEC -> BLOCKED
S7+ Game/Renderer/Main Loop -> NOT REACHED
```

## 8. 证据分级

### CONFIRMED

- `EXE Entry -> Base.dll ordinal_1`
- `Base+0x149C -> Base+0x1AA13B0`
- direct-launch 无 WeGame/TCLS/Client.exe/TCLS shared memory
- `WIN_IIPS_INIT_ERROR / 8189FEC` 是首个已验证硬阻塞

### STRONG

- `0x77F580 -> 0x77F8B3 -> 0x4FD9B0 -> 0x4FCEE0 -> 0x808650 -> 0x7E98F0 -> 0x6212C0`
- STUN host selection + mode globals `0x849413B`, `0x849B500`
- `-q` / `-qa` 可 bypass `WIN_NO_TCLS`

### CANDIDATE

- `0x4FD9B0` / `0x4FCEE0` 为 bootstrap dispatcher
- `0x808650` / `0x7E98F0` 为 subsystem dispatcher
- `0x6212C0` 为 network init
- Main Loop / Renderer / Filesystem / Game Init

### UNKNOWN

- 除 Base 外无其它 confirmed EXE external DLL dependency
- `.tvm0` 内部
- DLL 内部
- `8189FEC` source
- complete startup return path

## 9. 交付文件

```text
CODOL_STANDALONE_CORE_001_EXE_STARTUP_RECONSTRUCTION.md
exe_native_runtime_graph.csv
exe_init_clusters.csv
exe_game_init_candidates.csv
exe_mainloop_structural.csv
exe_renderer_candidates.csv
exe_filesystem_candidates.csv
exe_network_candidates.csv
exe_startup_stateflow.csv
exe_thread_map.csv
```

## 10. 最终结论

当前证据不支持“EXE 已具备完整自举启动到 MAIN LOOP”的结论。
当前证据支持：

```text
EXE 拥有 confirmed native entry + strong bootstrap/network dispatcher chain，
但首个已验证硬阻塞是 IIPS init / 8189FEC，
Game Init、Renderer、Filesystem、Main Loop 仍处于 CANDIDATE / UNKNOWN。
```

更准确的结论不是“启动失败原因”，而是：

```text
EXE 的独立 native runtime 路径尚未被完整恢复；
当前只确认到 bootstrap/network candidate，未确认到完整 game runtime。
```
