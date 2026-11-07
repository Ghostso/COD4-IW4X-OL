# 阶段记录：`[0x331C5C0]` 开关验证（poke 实验）

- **时间**：2026-09-26 13:30（Asia/Shanghai）
- **工作目录**：`D:\BaiduNetdiskDownload\使命召唤OL`
- **上游记录**：`SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md`

---

## 0. ★ 先纠正一条会误导后续的错误结论

另一会话在交接里写过：

> "The probe server's validator (0xB991A0) is hardcoded to require
> `auth_task==1`... the stage 10 protocol requires `auth_task==11`...
> **This fundamental architecture mismatch cannot be resolved server-side
> alone** - without modifying the client binary."

**这个结论不成立**，两处事实错误：

1. **`0xB991A0` 只管 stage 0。** 应答分派器 `0xB999C0` 按 stage 查表：

   ```asm
   00B999DD  jmp  0xB991A0                          ; stage 0  → 期望 auth_task==1
   00B999E2  push 0x80 / push 0x0B / call 0xB9A470  ; stage 10 → 期望 11
   ```

   **stage 10 根本不会走 `0xB991A0`**，所以"硬编码冲突"不存在。

2. **不需要改客户端二进制。** 全部工作都在服务端 + 一个运行期开关。

**⇒ 后续对话不要基于"必须改二进制"这条错误的结论推进。**

---

## 1. 本轮确认的核心事实：`[0x331C5C0]` 是路径开关

### 1.1 静态证据（`0x7F2B90`，子状态 6 的连接构造）

```asm
007F2BA0  cmp  dword ptr [0x331C5C0], 0
007F2BC0  je   0x7F2BFA              ; ==0 → 走 objB（降级路径）
007F2BC2  mov  eax, [0x84ABB08]      ; objA
007F2BDD  push 0x81A76A8             ; 字段3 HOST
007F2BE5  call 0xB88B80              ; ★ 构造 objA（真连接对象）
007F2BEA  mov  [0x84ABB08], eax
...
007F2BFA  mov  eax, [0x84ABB14]      ; objB
007F2C1D  call 0xB99090              ; ★ 构造 objB（auth 任务对象）
007F2C26  mov  [0x84ABB14], eax
```

而 `0x7F2DB0`（子状态 6 处理器）优先用 objA，objA 为空才回退 objB：

```asm
007F2DC5  mov esi, [0x84ABB08]       ; objA
007F2DCE  cmp esi, ebx
007F2DD0  jne 0x7F2DE0
007F2DD2  mov esi, [0x84ABB14]       ; objA 空 → 用 objB
```

### 1.2 `[0x331C5C0]` 的来源

`0x641600`（`ApplySettings`）在 `0x641BC8` 唯一写入，值取自栈槽 `[ebp-0x41C]`，
而该槽由配置串解析得到；**配置读不到就保持 `0`**。
函数开头 `0x641623` 先 `memset(0x331C5C0, 0, 0xD40)`。

### 1.3 运行期验证（`_poke_c5c0.py`）

```
{"ev":"poke","t":12.02,"before":0,"value":1,"ok":true,"after":1}

t=37.55  sw=0x1  uA50=2  sub=6  objA=0x39385e00  objB=0x0   ← ★ objA 出现
t=38.56  sw=0x1  uA50=2  sub=7  err=0x2e5
```

对照未 poke 的运行：`objA=0`、`objB=0x3ce353c8`（永远走降级路径）。

**⇒ 开关确实决定走哪条路径。假设成立。**

### 1.4 两个必须记住的操作细节

| 细节 | 说明 |
|---|---|
| **单次写入无效** | `ApplySettings` 每几秒重跑一次，会把值清回 `0`。实测 `t=12.02` 写入后 `t=15.03` 已被清零 |
| **必须持续压制** | 用 `--poke-window 30` 每 0.5 s 重写一次（共 60 次），值才保持在 `1` |
| **副作用** | 频繁 `VirtualProtectEx`/`WriteProcessMemory` 把整条时间线推迟约 18 s（`sub=6` 从 t≈19.5 → t≈37.5） |

---

## 2. 但开关只是**必要不充分**条件

即使 `objA` 已创建、两个服务都在监听、portproxy 正确：

```
objA = 0x39385e00（非 0）
/auth/ 探针（127.0.0.1:8443）  → 0 条连接
socket 服务（127.0.0.2:8444）  → 0 条连接
err = 0x2e5 (BD_EMPTY)
```

**⇒ 客户端仍未真正发起连接。**

---

## 3. BD 状态机（已完整反汇编，用于判读失败）

### 3.1 失败的判定链

```asm
; 0xC74F60 完成任务
00C74F69  mov edx, [eax+0x58]      ; = 0xC767F0
00C74F70  call edx                 ; 参数 = 1
00C74F74  je   0xC74F84            ; 返回假 → 失败
00C74F79  mov [esi+8], eax
00C74F84  ...
00C74F99  mov dword ptr [esi+4], 6 ; ★ [httpobj+4] = 6 = BD_FAILED
```

### 3.2 `0xC767F0`（可接受性判定）

```asm
00C767F3  mov edx, [ebp+8]         ; 参数
00C767F8  cmp edx, 5
00C767FD  jmp dword ptr [edx*4 + 0xC76854]

; 参数 == 1 时：
00C7680F  cmp dword ptr [ecx+4], 2 ; ★ 要求 BD 状态 == 2 (BD_INITIALIZING)
00C76813  sete al
```

### 3.3 状态枚举（`0xBAA1F0` 的名字表 → `0xD5A7xx`）

| 值 | 名称 |
|---:|---|
| 0 | `BD_UNINITIALIZED` |
| 1 | `BD_EMPTY` |
| 2 | `BD_INITIALIZING` ← **判定要求的** |
| 3 | `BD_PENDING` ← **实测停在的** |
| 4 | `BD_ABORTING` |
| 5 | `BD_DONE` |
| 6 | `BD_FAILED` |
| 7 | `BD_ABORTED` |

### 3.4 状态写入点（字节模式搜索）

| 值 | 地址 |
|---:|---|
| `=6` | `0xC74F99`、`0xC7511E`、`0xC75A60` |
| `=3` | `0xC750FA`（"请求已发出"之后） |
| `=2` | `0xC761AF`（"应答已到"，`0xC76184 call 0xAC9100` 之后） |

```asm
; 0xC750xx —— 设 PENDING(3)
00C750EE  call 0xC74270            ; 发起 HTTP 请求
00C750F5  je   0xC75119            ; 发不出 → 6
00C750FA  mov dword ptr [esi+4], 3 ; ★ BD_PENDING
00C75101  call 0xC73DF0            ; 推进
```

**⇒ `[httpobj+4]` 停在 3，说明 `0xC761AF`（设 2）从未执行 ⇒ 应答未被 BD 对象接收。**

### 3.5 关键字段（只读采样可拿到）

| 字段 | 含义 | 实测 |
|---|---|---|
| `[objB+0x160]` | BD 的 HTTP 子对象 | 有值 |
| `[httpobj+0x04]` | BD 状态 | 3 → 6 |
| `[httpobj+0x444]` | ② BD 状态（`0xC74FE0` 返回） | 0 / 1 |
| **`[httpobj+0x464]`** | **① HTTP 状态码（`0xC74FD0` 返回）** | **恒为 0** |
| `[httpobj+0x1C]` | 缓冲对象指针 | 有值（内容是**请求**字节） |

**`0xBAA2D0` 的判定**：

```asm
00BAA2DF  call [vt+0x34]           ; ① = [httpobj+0x464]
00BAA2EA  call [vt+0x38]           ; ② = [httpobj+0x444]
00BAA2FB  test edi, edi
00BAA2FD  je   0xBAA30E            ; ①==0 → 用 ② 查表 → BD_EMPTY(0x2E5)
00BAA308  lea eax, [esi-0xF]       ; ①==200 → 0x2BC(700)
```

**⇒ `[httpobj+0x464]` 永远是 0，所以恒走失败分支。**

---

## 4. 已排除的原因（全部有实测，避免重复试）

| # | 假设 | 结论 |
|---|---|---|
| 1 | `dwauth.ini` 缺失 | ❌ 已解决 |
| 2 | 端口非 443 | ❌ 已解决（443 硬校验，`sub` 到 7） |
| 3 | `auth_task` 映射 | ❌ 已修正（`{0:1,10:11,12:13,24:25,26:27}`） |
| 4 | ticket 格式 | ❌ 已修正（128B + `DE AD BD EF`） |
| 5 | TLS 套件 | ❌ 已解决（`TLSv1/AES256-SHA`，`SECLEVEL=0`） |
| 6 | `xid` 未定义崩溃 | ❌ 已修 |
| 7 | `Connection: close` | ❌ 已改 keep-alive |
| 8 | JSON 非法（`iv_seed` 空） | ❌ 已修 |
| 9 | 空值响应头 | ❌ 已修 |
| 10 | 端口重复监听 | ❌ 已修（`SO_EXCLUSIVEADDRUSE`） |
| 11 | portproxy 破坏数据 | ❌ 直连 443 验证排除 |
| 12 | `buildconfig.ini` 缺失 | ❌ 已建，无效 |
| 13 | 应答内容（5 个变体） | ❌ `f464` 恒为 0 |
| 14 | `[0x331C5C0]==0` | ✅ **确认是路径开关，但 poke=1 后仍失败** |

---

## 5. 当前环境（截至本记录）

```
portproxy:  127.0.0.1:443 → 127.0.0.1:8443
            127.0.0.2:443 → 127.0.0.2:8444
/auth/ 探针 127.0.0.1:8443
socket 服务 127.0.0.2:8444
dwauth.ini  127.0.0.1 / 0 / 127.0.0.2 / 443   （字段1/字段3 分指两个服务）
提权代理    pid 17900（admin）
```

**注意**：`netsh interface portproxy show all` **普通权限下返回空**，必须用提权代理查。

---

## 6. 下一步方向（未执行）

1. **采样 `[objA+…]`**：objA 才是真连接对象，看它的连接/状态字段（`0x7F2C33` 之后会载入 `cacert.pem`）
2. **降低 poke 频率**：改成只在 `t≈17–19s` 的窄窗口写入（避免拖慢时间线）
3. **查 `0xB88B80`**（objA 的构造器）之后**谁负责发起连接** —— `0x7F2C33` 只载入 CA，真正的 `connect` 调用还没定位
4. 考虑 `[0x331C5C0]` 的**正确来源**：它来自 TCLS 配置，**让 TCLS/TGP 跑起来**可能比 poke 更干净

---

## 7. 工具清单（本阶段新增）

| 文件 | 作用 |
|---|---|
| `_mainline\_bdfield_watch.py` | 只读采样 BD 对象（含 `http_444`/`http_464`） |
| `_mainline\_poke_c5c0.py` | 运行期改写 `[0x331C5C0]`，支持持续压制窗口 |
| `_mainline\_sweep_probe.py` | 自动扫描 `GET /` 应答变体 |
| `_mainline\_httpoj_scan.py` | 堆扫描 HTTP 对象（结果多为误报，慎用） |
| `_mainline\_conn_watch.py` | netstat 连接监控（对游戏无效，ACE 遮挡） |
| `_mainline\_auto_attempt.py` | 一次完整尝试（起服务+跑游戏+判读） |
| `_mainline\_direct443_setup.py` | 绕过 portproxy 直连 443 |
| `lobby_server\probe_response.txt` | `GET /` 应答可配置（`status=` / `body=` / `header=`） |
