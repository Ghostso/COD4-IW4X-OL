# 01 — `0x350170` 路径归属 / DEMO PATH ATTRIBUTION

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> 客户端 SHA256 `353754047DBBFE3AFBF6C7D97DE3FACA785B3D5D5E34A9053C820EE78814D6E1`
> 恢复镜像 `codol2697-static-candidate.bin`，ImageBase `0x400000`（VA = RVA + 0x400000）。
> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`
> 纪律：不因错误字符串或函数名单独裁定路径归属。

---

## 1. 结论摘要

| 主张 | 裁定 |
|---|---|
| `0x350170` 属于 demo/回放处理路径 | **INFERRED（强）**，未达 PROVEN |
| `0x350170` 属于实时网络路径 | **未发现支持证据**（在指定范围内） |
| 可正式从实时网络候选链排除 | **不能**（见 §6） |

**核心证据：** `0x350170` 的两条上游入口最终都由 **demo 控制台命令**驱动，而非网络接收。

## 2. 上游调用链（全量 BFS，DIRECT）

以 `0x350170` 为根做反向调用图 BFS（深度 4），上游**收敛到 9 个函数**：

```
depth 0 : 0x350170
depth 1 : 0x08F1D0, 0x3512A0
depth 2 : 0x09CFE0, 0x34E7C0, 0x3519F0, 0x351A10, 0x356580
depth 3 : 0x1A9060
depth 4 : 0x1A9760
```

## 3. `0x34E7C0` 是 demo 控制台命令回调（DIRECT，决定性）

`0x34DF80` 是注册函数，在 `0x34E1B0` 处注册命令回调：

```asm
34E19B  mov dword [0xDD4BF44], 0x74E7C0    ; ← 回调 = 0x34E7C0
34E1AB  mov esi, 0xCD61EC
34E1B0  call 0x59DCA0                       ; Cmd_AddCommand(name, callback)
```

命令名字符串（`_data/out_t37_names.txt`）：

| VA | 内容 |
|---|---|
| `0xCD61C4` | `cl_demo_timedemo` |
| **`0xCD61D8`** | **`cl_demo_jumptostart`** |
| `0xCD61EC` | `cl_demo_keyboard` |
| `0xCD6200` | `cl_demo_keyboardcomplete` |

**`0x34E7C0` 对应 `cl_demo_jumptostart`（DIRECT）。**

同一注册函数还写入 `cl_demo_play`（`0xCD61B4`）及 cvar `917`–`935`（`0xCD6184`–`0xCD61B0`），整块属于 demo 子系统。

**`0x34E7C0` 的数据指针引用唯一**：`0x34E1A1`（即上述注册表项）——无其他调用者（DIRECT）。

## 4. `0x8F1D0` 的 demo 状态门（DIRECT）

```asm
08F1D3  mov ecx,[0x1BBBCFC]        ; demo/回放状态机
08F1DC  cmp ecx,7
08F1DF  jl  0x48F4B0               ; 状态 < 7 → 直接返回（不调 0x350170）
08F1E5  ...
08F22A  lea edi,[eax+0x1BBBCFC]
08F230  mov eax,[edi]
08F232  cmp eax,7
08F235  jl  0x48F24A
08F237  cmp eax,9
08F23A  jge 0x48F24A
08F23C  mov eax,ebx
08F23E  call 0x750170              ; ← 仅当状态 ∈ [7,9) 才调用
08F24A  call 0x5A96A0
08F251  call 0x750170
08F261  cmp ecx,9
08F264  jne 0x48F4B0               ; 状态 != 9 → 返回
08F26A  ...
08F29F  cmp dword [0x1BBBCFC],0xA
```

**`0x1BBBCFC` 是 demo/回放状态机**（取值范围 0–10，`_data/out_state_var.txt` 共 166 处引用），其写入点集中在 `0x8Fxxx`/`0x9Cxxx`/`0x9Dxxx`（demo 控制簇）。

## 5. `0x8F1D0` 的错误处理引用 demo 错误码（DIRECT）

`0x8F1D0` 的调用者 `0x350170` 越界分支：

```asm
350245  push 0xCD6384
35024A  push 2
35024C  call 0xDDAB8AC
```

字符串 `0xCD6384` = **`EXE_ERR_PROCESS_DEMO_FILE_FAILED`**（`_data/out_t10_batch2`）。

**注意：** 按任务要求，**该字符串单独不足以裁定**；它与 §3、§4 的状态机/命令注册证据**合并**才构成强推断。

## 6. 读取器归属（DIRECT）

`[client+0x89244]` 是**可插拔读取函数指针**，全镜像仅 3 处写入：

| 站点 | 写入值 | 场景 |
|---|---|---|
| `0x35141E` | `0x752570` | 网络读取器（读自 `[+0x8048]` 环形缓冲） |
| `0x3515D9` | `0x74F090` | demo 读取器（失败报 `EXE_ERR_READING_DEMO`） |
| `0x356701` | `0x74F090` | demo 读取器 |

`0x356580`（`0x34E7C0` 调用的 demo 装载函数）在 `0x356701` 安装 demo 读取器后，于 `0x356722` 调用 `0x8F1D0`：

```asm
356701  mov dword [esi+0x89244], 0x74F090
356711  push 0x8020 / push ecx / call edx      ; demo 读取
356722  call 0x48F1D0
```

**这是 demo 链的决定性汇合点（DIRECT）。**

## 7. 未证实的实时网络关联

| 检查 | 范围 | 结果 |
|---|---|---|
| `recv`/`recvfrom` IAT 调用点（9 个函数） | 全 `.text` | 8 层内**未**到达 `0x350170`/`0x3547D0`/`0xA2660` |
| `0x350170` 数据指针引用 | 全镜像 | **0** |
| `0x350170` 上游是否含 socket 句柄/网络缓冲 | 9 个上游函数 | 未发现 |

**说明（按任务纪律）：** 负搜索只记为“在指定范围内未发现”，**不构成 REFUTED**。

## 8. 不能据此下结论的证据

| 证据 | 为何不足 |
|---|---|
| `EXE_ERR_PROCESS_DEMO_FILE_FAILED` 字符串 | 单独可属任何路径；需与状态机/注册证据合并 |
| 函数位于 `0x34xxxx`–`0x35xxxx` 簇 | 地址簇不等于路径归属 |
| `0x352570` 名为“网络读取器” | 命名来自其环形缓冲行为，非路径证明；`0x74F090` 亦写入同一 `+0x89244` |

## 9. 裁定

**`0x350170` 归属 demo/回放路径：INFERRED（强）。**

- 支持：命令回调 `cl_demo_jumptostart`（`0x34E7C0`）+ demo 状态机门（`0x1BBBCFC ∈ [7,9)`）+ demo 读取器安装（`0x74F090`）+ demo 错误码。
- 未排除的替代解释：`0x8F1D0` 可能同时被实时路径以相同状态值调用（未发现证据，但未穷尽间接分派）。
- **因此不能宣称 PROVEN，也不能据此正式排除实时网络候选链。**
