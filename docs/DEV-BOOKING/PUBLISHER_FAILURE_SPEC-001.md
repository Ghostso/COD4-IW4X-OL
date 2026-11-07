# PUBLISHER_FAILURE_SPEC-001

> EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 定位
> 纯静态（image_best.bin）+ 已有运行期日志比对
> 未修改 Server / Golden / 4 patch / KDF hook / 客户端
> 未启动 Booking Server，未发送 6/14，未修复任何文件

---

## 0. 结论摘要

| 项 | 值 | 等级 |
|---|---|---|
| ERROR_STRING_XREF | `0x0066A827` 唯一引用 `0x00DC9C6C` | CONFIRMED |
| FAILURE_FUNCTION | `0x0066A650` | CONFIRMED |
| FAILURE_CONDITION | 同一个 publisher 文件连续 3 次加载失败 | CONFIRMED |
| PUBLISHER_FILE | 一组 `.info` 发行方文件（见 §4） | CONFIRMED |
| FAILURE_REASON | 本地文件 NOT_FOUND | CONFIRMED |
| GAME_STAGE | 内容/发行方文件准备（非 Booking 前置校验） | STRONG_CANDIDATE |

一句话：

> 客户端在进入剧情/靶场时，尝试加载一组发行方（publisher）
> `.info` 文件；这些文件本地不存在，连续 3 次重试失败后，
> 调用 `0x66A650` 弹出 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`。

---

## 1. P0-1：错误字符串引用

锚点：

```
0x00DC9C6C  "EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE"
```

全镜像 dword 引用扫描：

```
0x00DC9C6C refs = { 0x0066A827 }     （唯一）
```

该点是一段 `push imm32`：

```asm
0066A826  push 0xDC9C6C
0066A82B  push 0
0066A82D  call 0x4F82E0          ; fatal error 显示函数
0066A832  add esp, 8
```

### ERROR_STRING → ERROR_CONSTRUCTION → ERROR_DISPLAY

```
0x00DC9C6C  (字符串)
   ↓ push imm32 @0x0066A826
0x004F82E0  (fatal error / message box 显示)
   ↓
致命错误弹窗（详见运行期窗口抓取）
```

**ERROR_STRING_XREF = CONFIRMED**

---

## 2. P0-2：Fatal Error 生成函数

函数入口：`0x0066A650`

签名（从寄存器/栈使用推断）：

```
0x66A650  thiscall
  ecx = 某个上下文
  [ebp+8]  = publisher index (ebx)
  [ebp+0xC] = 参数
  [ebp+0x10] = 字节参数
```

关键路径：

```asm
0066A654  cmp byte [0x849BA3D], 0
0066A65B  push ebx
0066A65C  mov ebx, [ebp+8]
0066A65F  mov eax, [ebx*4 + 0xDA9FC8]    ; publisher 类型枚举
0066A667  mov [ebp+8], eax
0066A66C  mov eax, [0x84ABA50]
0066A671  cmp eax, 5
0066A674  ja 0x66A67D
0066A676  jmp [eax*4 + 0x66A6F8]         ; 6 路分支表
```

分支表 `0x66A6F8` 指向 6 个 publisher handler，其中一个进入：

```asm
0066A6E4  call 0x7F9830                  ; 尝试加载/处理 publisher 文件
0066A6EC  test al, al
0066A6EF  setne al                       ; 成功 -> 1
```

失败重试路径：

```asm
0066A7E9  cmp byte [edi+0xE57A54], 0     ; 是否允许重试
0066A7F0  jne 0x66A803
0066A7F2  mov ecx, [esi]
0066A7F4  push 1
0066A7F6  call 0x512A10                  ; 记录/退避
0066A803  inc dword [ebx+0xC7AEAC8]      ; 重试计数 +1
0066A809  cmp dword [ebx+0xC7AEAC8], 3
0066A810  jg 0x66A826                    ; ★ 超过 3 次 -> FATAL
0066A812  mov edi, [edi*4 + 0xDA9FC8]
0066A819  push edi
0066A81A  call 0x7F9830                  ; 再次尝试
0066A822  test al, al
0066A824  jne 0x66A835                   ; 成功 -> 返回
0066A826  push 0xDC9C6C                  ; ★ FAILURE
0066A82D  call 0x4F82E0                  ; 显示致命错误
```

**FAILURE_FUNCTION = 0x0066A650（CONFIRMED）**

---

## 3. P0-3：失败条件

```
CONDITION
  publisher 文件加载失败（0x7F9830 返回 0）
    ↓
  允许重试（[edi+0xE57A54] != 0）
    ↓
  重试计数 [ctx+0xC7AEAC8] 自增
    ↓
  cmp [ctx+0xC7AEAC8], 3
    ↓ 超过 3 次
FAILURE CODE
  EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE @0x66A826
```

即：

**FAILURE_CONDITION = 同一个 publisher 文件连续 3 次加载失败（CONFIRMED）**

对应运行期证据（`lobby_srv.log`，20:07:58）：

```
缺 mp_playlists_shipRetail_1.0.0.info
缺 activities_v1.info
缺 configs_s.info
缺 daily_challenge_config.info
缺 broadcast.info
缺 tlogconfig.info
缺 market_ui.info
缺 market-down.info
缺 whitelist_tester.info
缺 MOTD.info
```

即重试确实发生，且全部失败。

---

## 4. P0-4：失败对象（PUBLISHER_FILE）

`0x66A650` 的调用者 `0x50E9B1` / `0x50EA7B` 位于一个
publisher 文件分发表，每个分支 `push` 一个文件名：

| 地址 | 字符串 |
|---|---|
| `0x00DBDEBC` | `activities_v1.info` |
| `0x00DBDED0` | `broadcast.info` |
| `0x00DBDEE0` | `tlogconfig.info` |
| `0x00DBDEF0` | `market_ui.info` |
| `0x00DBDF00` | `market-down.info` |
| `0x00DBDF14` | `whitelist_tester.info` |
| `0x00DBDF2C` | `MOTD.info` |
| `0x00DBDF38` | `daily_challenge_config.info` |

另有 lobby 日志中同样出现的：

```
mp_playlists_shipRetail_1.0.0.info
configs_s.info
```

### PUBLISHER_FILE = 上述 `.info` 发行方文件（CONFIRMED）

### FAILURE_REASON

运行期日志明确记录这些文件为“缺”（NOT_FOUND）：

```
-> 缺 activities_v1.info
-> 缺 broadcast.info
...
```

```
FAILURE_REASON = NOT_FOUND (CONFIRMED)
```

不是 HASH_FAILED / VERSION_FAILED / PARSE_FAILED /
DOWNLOAD_FAILED —— 文件根本没有被找到。

---

## 5. P0-5：本地资源检查

检查对象：Golden 沙箱与 Golden 包。

```
run_codol_001\sandbox_datafix_20260929
  *.info 文件数量 = 0

GOLDEN-LOBBY-001\REF_LOBBY_KIT\publisher_files
  EXISTS = False
```

因此：

```
EXPECTED_PATH = <publisher_files>\<name>.info（客户端内部搜索路径）
ACTUAL_PATH   = 不存在
EXISTS        = False
SHA256        = N/A
```

### 结论

```
缺失对象 = 发行方 .info 文件（publisher files）
本地状态 = 完全没有
```

**未复制、未替换、未生成任何文件。**

---

## 6. P0-6：是否属于腾讯旧更新/发布系统

证据：

- 加载路径经 `0x803830`（全局网络单例）→ `0xB80EC0`（资源/发布方查询）
- 文件名为腾讯发行体系命名（`market_ui.info`、`MOTD.info`、
  `whitelist_tester.info`、`daily_challenge_config.info`）
- 客户端把这类文件标为 “EXE_DOWNLOAD_...” 前缀，属下载/发布方资源

但**没有**证据表明它必须依赖仍然死亡的腾讯线上服务：
这些 `.info` 是**可本地提供的配置文件**，客户端也会走本地资源/HTTP
两条路径（`0x7F9830` 内部同时尝试本地与网络）。

```
EXTERNAL_SERVICE_DEPENDENCY = UNKNOWN
（未证实必须依赖线上服务；也未证实纯本地即可）
```

按指令：不恢复 WeGame/TCLS，不伪造服务。本阶段仅定位。

---

## 7. P0-7：GAME_STAGE 判定

发生时机（运行期）：

```
20:02:22  大厅握手完成，进入 Lobby，keepalive 正常
20:03~20:06 用户点击进入剧情/靶场
20:07:28  大厅连接被客户端关闭
20:07:58  客户端请求 9 个 publisher .info 文件，全部缺失
           随后弹出 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
```

关键：`mmbook`（6/14）在整个过程中 **0 命中**。

因此它**不是 Booking 前置资源检查**（Booking 尚未开始），
也不是 Booking 协议失败。

```
A. Booking 前置资源检查            = REFUTED
B. 内容/地图/playlist 初始化        = STRONG_CANDIDATE
C. 腾讯旧更新/发布系统              = CANDIDATE（可本地化，未证实强依赖）
```

理由：缺失文件包含 `mp_playlists_shipRetail_1.0.0.info`
（playlist 表）、`configs_s.info`、`market_ui.info` 等，
属于**客户端启动/内容准备阶段的发行方配置加载**，
发生在匹配（findSessions / mmbook）之前。

**GAME_STAGE = CONTENT/PUBLISHER_CONFIG_LOAD（STRONG_CANDIDATE）**

---

## 8. P0-8：与已有资源的关系

已确认的关系：

```
PUBLISHER_FILE (.info)
   → 客户端内容/playlist/市场初始化数据
   → 属于“发行方发布文件”层（publisher）
   → 不是 IFS/FF/PAK 本体，而是它们的索引/配置描述
```

即这些 `.info` 是**描述性配置**，可能指向 IFS/FF/PAK；
文件本身缺失导致后续内容初始化中断，而不是资源文件损坏。

```
PUBLISHER_FILE → RESOURCE 映射 = UNKNOWN（未解析 .info 内容）
GAME_INIT_STAGE               = CONTENT/PUBLISHER_CONFIG_LOAD
```

未修改任何资源。

---

## 9. 成功标准核对

| # | 目标 | 结果 |
|---|---|---|
| 1 | ERROR_STRING_XREF | CONFIRMED：`0x0066A827` |
| 2 | FAILURE_FUNCTION | CONFIRMED：`0x0066A650` |
| 3 | FAILURE_CONDITION | CONFIRMED：重试 >3 次失败 |
| 4 | PUBLISHER_FILE | CONFIRMED：一组 `.info` 文件 |
| 5 | FAILURE_REASON | CONFIRMED：NOT_FOUND |
| 6 | GAME_STAGE | STRONG_CANDIDATE：内容/发布方配置加载 |

---

## 10. 停止条件

已确认：

```
FAILURE_FUNCTION  = 0x0066A650
FAILURE_CONDITION = publisher .info 加载连续失败 >3 次
PUBLISHER_FILE    = activities_v1/broadcast/tlogconfig/market_ui/
                    market-down/whitelist_tester/MOTD/
                    daily_challenge_config/mp_playlists/configs_s .info
```

按停止条件，本阶段停止扩大扫描。

**未修复任何文件。**

---

## 11. 下一阶段待决策（不执行）

两个方向，由用户决定：

```
方向 A：RESTORE_LOCAL_FILE
  从原始客户端/备份/安装包中找到这些 .info 文件并放回本地搜索路径。
  需要先确认客户端期望的目录（publisher_files?），
  以及 .info 是否含签名/校验。

方向 B：RESTORE_LOCAL_PUBLISHER_SERVICE
  由本地服务在对应请求上返回这些 .info。
  需要先确认客户端走的是本地文件还是网络请求，
  以及具体 opcode/URL。
```

在决策前不得修改 Server，不得发送 6/14 response。

---

## 12. 纪律核对

```
Server 修改              = 无
Golden 修改              = 无
4 个 Lobby patch 修改    = 无
KDF hook 修改            = 无
客户端修改               = 无
Booking Server 启动      = 无
6/14 发送                = 无
ACE 移除/绕过/配置       = 无
文件复制/替换/生成       = 无
```

