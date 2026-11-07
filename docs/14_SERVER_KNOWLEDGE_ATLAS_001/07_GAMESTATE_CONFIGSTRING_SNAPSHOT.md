# 07 — Gamestate / Configstrings / Snapshot 字段级档案

> 三服务端并列。2697 为指令级 VERIFIED；OLD/1113 为源码级 VERIFIED。

## 1. Gamestate

### 1.1 OLD/1113（legacy）

| 项 | 值 | 证据 |
|---|---|---|
| opcode | `0x02` | EV-Old-Legacy |
| 编码函数 | `CODOL_WriteGamestate` RVA 0xA865A | EV-Old-Legacy |
| 终止符 | `0x05` | EV-Old-Legacy |
| 发送前 | `SV_SendClientGameState`（sv_client.c:2160）→ CS_PRIMED | EV-Old-Connect |

### 1.2 2697（VERIFIED 字段顺序）

`_CODOL2697_WriteGamestate` RVA 0xA21B8；入口门控 `_CODOL2697_WriteNativeGamestate` RVA 0xA3DAB。

```
03 <long> <map\0> "mp"\0 <long> <configstrings:04…> <long> <long> 06
    RVA 0xA224C 起                                   RVA 0xA22F8
```

| 字段 | 类型 | 来源 | 等级 |
|---|---|---|---|
| opcode | u8 = `0x03` | `_CODOL_WriteByte 3` | VERIFIED |
| version | long | state[0] | VERIFIED（宽度）/ BLOCKED（语义） |
| map | NUL 字符串 | state+4 | VERIFIED（形状）/ BLOCKED（语义） |
| "mp" | NUL 字符串 | 常量 | VERIFIED |
| field4 | long | state+8 | VERIFIED（宽度）/ BLOCKED（语义） |
| configstrings 块 | 0x04…0x06 | `_WriteConfigstrings` | VERIFIED（嵌套位置） |
| fieldC | long | state+0xC | VERIFIED（宽度）/ BLOCKED（语义） |
| field8 | long | state+0x8 | VERIFIED（宽度）/ BLOCKED（语义） |
| 终止符 | u8 = `0x06` | RVA 0xA22F8 | VERIFIED |

### 1.3 2697 门控（本档案最关键发现之一）

见 `03` §6。双条件：资源对象 `+0x78F4` 与 注册结构 `+0x6408`。缺失即 `return 0`。

## 2. Configstrings

| 项 | OLD/1113 | 2697 |
|---|---|---|
| opcode | `0x03` | `0x04` |
| 编码函数 | `CODOL_WriteConfigstrings` RVA 0xA857F | `_CODOL2697_WriteConfigstrings` RVA 0xA0468 |
| count | — | short @ RVA 0xA0807，上限 `0x1DD7` |
| 终止符 | `0x05` | `0x06` @ RVA 0xA0997 |
| 数量语义 | 6519 条；武器从 5362 起 | BLOCKED（body bit 编码） |
| body | — | PARTIAL：`bits_a ≤ 0x7FF`、`bits_b ≤ 0x3FF`、payload bits `0x0A/0x07/0x04`、12-bit 子记录 |

**未决：** index 位打包、字符串索引规则、数组编码、客户端 consumer（全 BLOCKED）。

## 3. Snapshot

### 3.1 OLD/1113

- `SV_WriteSnapshotToClient`（sv_snapshot.c:224）；作者自述**仍用 IW3 序列化器**，未收敛（EV-Old-Incomplete）。

### 3.2 2697（VERIFIED 调用序列）

```
_CODOL2697_WriteSnapshot            RVA 0xA4FA0  (0xA4FF7 包装调用 ↓)
  └─ _CODOL2697_WriteSnapshotReached RVA 0xA4860
       ├─ 初始写 0x00                 RVA 0xA495D  (STATIC-INFERENCE：不证明是网络 opcode)
       ├─ 序列 long                   RVA 0xA496E
       ├─ player fields / player arrays
       ├─ animations
       ├─ actors / entities
       ├─ clients
       ├─ glass  → 内部 0x06          RVA 0xA4CAF
       ├─ HUD (_CODOL2697_ReachHud)   RVA 0xA4CEE
       ├─ 第二遍 actors / entities
       └─ 区域复制：
            0x728                  RVA 0xA4EBB
            0x2C38                 RVA 0xA4EDF
            count * 0x1F8          RVA 0xA4F3F
            count * 0x13C          RVA 0xA4F61
            count * 0x5C           RVA 0xA4F7D
```

- 另一调用点：`_CODOL2697_PrepareHistory`（RVA 0xA249D）→ `0xA26EB`。
- **外层终止符选择：** `_SV_EndClientSnapshot` RVA 0x86F7D 的 0x87104：
  - `_CODOL_Target2697ArchivesActive == false` → 写 `0x05`
  - `== true` → 写 `0x06`

### 3.3 内部 `0x06` 的角色（STATIC-INFERENCE）

- `0xA4CAF` 在 `_CODOL_WriteGlass` 之后写 `6`，但**之后仍用同一 writer 继续写入**（HUD、第二遍 actors/entities）。
- 因此它更可能是 **内部子记录/阶段终止符**，**不能**单独证明它是整条网络消息的最终 EOF。
- 任务书要求区分“内部状态标记”与“线上字节”——这正是典型案例。

## 4. 客户端侧状态（BLOCKED）

| 项 | 状态 | 证据 |
|---|---|---|
| `0x03` gamestate 网络读取 | BLOCKED | 仅 `gamestateupdate %d`（RVA 0x8B8378）引用点 0x56893/0xA2994；0xA2660 为候选 |
| `0x04` configstring 读取 | BLOCKED | `EXE_CONFIGSTRINGMISMATCH` 无 reader |
| `0x06` EOF 终止 | NOT-OBSERVED / BLOCKED | `UNEXPECTED_EOF` 无直接代码引用 |
| `0x02` reliable 分派 | BLOCKED | 见 `05` §4.4 |
| snapshot delta 解码 | BLOCKED | 候选 `0x6E060` / `0x6D340`（后者附近有与 `5`、`6` 的比较） |

## 5. 字段级对照表（三服务端 × 三类消息）

| 消息 | OLD | 1113 | 2697 | 客户端消费 |
|---|---|---|---|---|
| gamestate opcode | 0x02 | 0x02 | 0x03 | BLOCKED |
| gamestate 终止 | 0x05 | 0x05 | 0x06 | BLOCKED |
| configstring opcode | 0x03 | 0x03 | 0x04 | BLOCKED |
| configstring 终止 | 0x05 | 0x05 | 0x06 | BLOCKED |
| snapshot | IW3 serializer | IW3 serializer | `0xA4FA0→0xA4860` | BLOCKED |
| 外层终止 | 0x05 | 0x05 | 0x05/0x06（按 archive 激活） | BLOCKED |
| 可靠命令 | 0x01 + string | 0x01 + string | 0x01 + string / **0x02 + long + short + data** | BLOCKED |

## 6. 结论

1. 2697 的 gamestate/configstring/snapshot **字段顺序与终止符已在服务端指令级确认**。
2. 但**语义字段名**（state[0]/+4/+8/+0xC）与 **configstring body 位编码** 仍 BLOCKED。
3. **服务端能写 ≠ 客户端能读**：客户端消费侧全部 BLOCKED/NOT-OBSERVED。
4. 内部 `0x06` vs 外层 `0x05/0x06` 必须区分，不能混为一谈。
---

# === 追加：指令级复核（UPDATE-2, 2026-10-12） ===

## 内部 `0x06` 的调用顺序（已证实）

```
RVA 0xA4CA4  mov [esp+4],6
RVA 0xA4CAF  call 0x499551        ← 写 6（内部标记）
RVA 0xA4CEE  call 0x49f2e5        ← ReachHud，之后仍继续写
RVA 0xA4D4B  call 0x49c718
RVA 0xA4D99  call 0x4a1a65        ← WriteEntities
```

→ **内部 `0x06` 不是外层 EOF**（证据 EV-2697-SnapshotOrder；H-PRO-03 升为 CONFIRMED）。

## 注册门控的格式与校验链（已证实）

```
格式串（VA 0x7C42A0 / 0x7C42C0 / 0x7C42E4）：
  "codol2697-registration %u %x %u"
  "codol2697-registration %u %x %u %c"
  "codol2697-registration %u %x %u %u %x %c"

_CODOL2697_ReadRegistration  RVA 0xA3EA0
  mov eax,0xc8d8 ; call 0x74e900 ; sub esp,eax     ; 栈帧
  lea eax,[ebp-0xc820] ; memset(...,0,0xc814)      ; 本地 blob, 0xC814
  fopen → fgets(…,0x80) → sscanf(…) → cmp eax,3    ; 必须 3 字段
  lea eax,[edx-1] ; cmp eax,1 ; ja fail            ; kind ∈ {1,2}
  CRC32 校验通过 → mov dword [ebp-0x6418], 1       ; = blob + 0x6408
  memcpy(0x14973B00, [ebp-0xC820], 0xC814)         ; 拷入全局注册结构
```

**偏移算术：** `[ebp-0xC820]` + `0x6408` = `[ebp-0x6418]` ✔（证据 EV-2697-RegFmt3）。

## 磁盘样本交叉验证

`evidence\client-registration2697.txt` 首行 `codol2697-registration 2 6b6fb5d0 180 139 f78302fe`
→ `kind=2`（∈{1,2} ✔）、`%x`=0x6b6fb5d0、随后 180 / 139 / f78302fe，与 `%u %x %u %u %x %c` 变体形状一致。
