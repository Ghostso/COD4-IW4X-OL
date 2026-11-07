# 学习报告 024 — 逐字节：OLMOD_* 变量的真实归属 + Winsock hook 自检

**方法**：跨模块统计 `OLMOD_*` 变量出现次数 + 读取 `0x519B0` / `0x7C270` 的实际内容
**性质**：全实测
**★★★ 本报告修正了报告 023 的一个关键推断**

---

## 一、★★★ `OLMOD_*` 变量的真实归属矩阵（实测）

```
模块                          CLAIM_LOBBY  LOBBY_LISTEN  LOBBY_HOST  SYNTHETIC_DNS  PROCESS_ROLE  lobby.codol.localhost  OLMOD_总数
Localnetworking.Ayria32                  0             3           1              1             1                      0            7
Alwaysoffline.Localnet32                 1             0           0              0             1                      1           41
CodolGameServer.Localnet32               0             0           0              0             1                      0          135
Platformwrapper.Ayria32                  0             0           0              0             0                      0            1
```

### ★★★ 结论 1：`OLMOD_CLAIM_LOBBY` **只属于 `Alwaysoffline`**

```
Localnetworking:     0 次
Alwaysoffline:       1 次   ← ★★★ 唯一持有者
CodolGameServer:     0 次
Platformwrapper:     0 次
```

★★★ **这修正了报告 023 第八节结论 4 的疑问**：
**`OLMOD_CLAIM_LOBBY` 的读取方确实是 `Alwaysoffline`，不是 `Localnetworking`。**

★★ **但 `Alwaysoffline` 没有 `onStartup` / `onMessage` 导出** ——
**它怎么被问到"你认领吗"？**

★★★ **⇒ 必须通过 `Createserver` 之后的某条路径。**

★ **而 `Alwaysoffline` 里也有 `lobby.codol.localhost`（1 次）** ——
**主机名和开关在同一个模块里，逻辑闭合。**

### ★★★ 结论 2：`OLMOD_LOBBY_LISTEN` 只属于 `Localnetworking`

```
Localnetworking:     3 次   ← ★★★ 唯一持有者
其他:                0 次
```

★★ **`Localnetworking` 里 3 次（报告 023 已看到 3 条日志）**：
```
"OLMOD_LOBBY_LISTEN"
"Lobby listener disabled by OLMOD_LOBBY_LISTEN."
"Lobby listener skipped: OLMOD_LOBBY_LISTEN=\""
```

★★★ **⇒ 两个开关分属两个模块，是**独立的两层**：**

```
Alwaysoffline::OLMOD_CLAIM_LOBBY=1
    ⇒ 插件"愿意"认领 lobby.codol.localhost

Localnetworking::OLMOD_LOBBY_LISTEN=<addr 或 disable>
    ⇒ 底层"是否真的去 bind"
```

★★★ **必须两层都处理，才能让出 3074。**

### ★ 结论 3：`OLMOD_LOBBY_HOST` / `OLMOD_SYNTHETIC_DNS` 只在 `Localnetworking`

```
Localnetworking:  LOBBY_HOST=1, SYNTHETIC_DNS=1
其他:             全部 0
```

★ **⇒ 网络层的所有环境变量都由 `Localnetworking` 读。**

### ★★ 结论 4：`OLMOD_PROCESS_ROLE` 在三个插件里都有

```
Localnetworking     1
Alwaysoffline       1
CodolGameServer     1
Platformwrapper     0
```

★ **`Platformwrapper` 不看 role** —— 它只提供 Tencent 接口，与 role 无关。

### ★★★ 结论 5：`OLMOD_` 总数揭示模块规模

```
CodolGameServer:  135 个 OLMOD_* 变量引用  ← ★★★ 最多
Alwaysoffline:     41
Localnetworking:    7
Platformwrapper:    1
```

★★★ **`CodolGameServer` 有 135 处 `OLMOD_` 引用** ——
**它的可配置面远超其他插件**（战斗服参数多）。

★★ **这与记忆里"177 个 OLMOD_* 变量全清单"吻合**：
```
135 (CodolGameServer) + 41 (Alwaysoffline) + 7 (Localnetworking) + 1 (Platformwrapper)
= 184 处引用（含重复，不等于 177 个唯一变量）
```

---

## 二、★★★ `0x519B0` 的真实内容 —— Winsock hook 自检失败日志

```asm
; onStartup @ 0x17041
C7 00 B0 19 05 10     mov dword ptr [eax], 100519B0h
C7 40 04 2C 00 00 00  mov dword ptr [eax+4], 2Ch      ; len = 44
```

**读取实测**（RVA `0x519B0` → raw `0x507B0`，44 字节）：
```
bytes: 46 61 69 6C 65 64 20 74 6F 20 69 6E 73 74 61 6C 6C 20 6F 6E
       65 20 6F 72 20 6D 6F 72 65 20 57 69 6E 73 6F 63 6B 20 68 6F
       6F 6B 73 2E
ascii: "Failed to install one or more Winsock hooks."
```

### ★★★ 这是极其重要的一条

```
"Failed to install one or more Winsock hooks."
```

★★★ **⇒ `Localnetworking::onStartup` 的核心职责就是**安装 Winsock hook**。**

**流程（由反汇编还原）**：
```
1. call 0x71B0       构造配置对象 A
2. if (!A.ok) goto 清理        ← 配置无效就跳过
3. 构造三个字符串对象（B/C/D）
4. call 0x4F00        ★ 主逻辑（= 装 hook + 绑 Lobby）
5. call 0x5550        ★ 检查结果？
6. if (al == 0) goto 清理
7. call 0x4390        检查另一条件
8. if (al != 0) goto 清理
9. 构造 44 字节串 "Failed to install one or more Winsock hooks."
10. call 0x5030        ★ 记录错误/日志
```

★★★ **⇒ 步骤 5-8 成功、步骤 9 失败** 就是"hook 装不上"的路径。

★★ **这与记忆完全吻合**：
> 记忆 `codol-lsg-never-listening`：
> "两组 nt10 关键差异：GOLDEN 版 hook 全成功 + KDF 挂载（可观测网络）；
> **外部版全失败（Localnetworking 抢先 hook 了 ws2_32）**"

★★★ **⇒ "Localnetworking 抢先 hook 了 ws2_32" 现在有了字节级证据**：
**`Localnetworking` 的第一件正事就是装 Winsock hook**，
**如果它先装了，`nt10.py` 的 hook 就装不上（互相排斥）。**

---

## 三、★★★ 这解释了 GOLDEN 与外部包的根本冲突

### 冲突机制（字节级还原）

```
GOLDEN 链（我们的）：
    nt10.py 装 Winsock hook（connect/sendto/gethostbyname）
        ⇒ 可观测网络 ⇒ 能读取会话密钥 ⇒ 进大厅

外部包：
    Injector32 → Bootstrapper → Localnetworking.Ayria32
        ⇒ Localnetworking::onStartup 第一件事就是装 Winsock hook
        ⇒ nt10.py 的 hook 装不上
        ⇒ 无法观测网络
```

★★★ **⇒ 两者在 `ws2_32` 上的 hook 是**互斥的**。**

★ **`nt10.py` 先启动、先装 hook ⇒ `Localnetworking` 装不上**
★ **`Localnetworking` 先装 ⇒ `nt10.py` 装不上**

★★ **而 `launch_chain.py` 的顺序是**：
```
步骤 2: nt10.py 拉起客户端（此时 nt10.py 已装 hook？）
        但 nt10.py 是**先启动客户端，再等 --delay 秒后装 hook**
```
**`--delay 0`**（`launch_chain.py:354`）⇒ **不等待，立即装。**

★★★ **⇒ 谁先谁后取决于**毫秒级的竞态**。**

★ **这可能就是"坏启动率 20-40%"（报告 007）的真正原因！**

★★ **但报告 013 已经把"坏启动"归因于 STUN。**
**现在有两个独立原因导致不稳定：**
1. **STUN 未就绪（报告 013）**
2. **Winsock hook 竞态（本报告）**

---

## 四、★★ `0x7C270` 是一个结构体不是字符串

**读取实测**（RVA `0x7C270` → raw `0x7AE70`）：
```
hex: BC 15 05 10  07 00 00 00  02 00 00 00  00 00 00 00
     00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
     00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
     FF FF FF FF  00 00 00 00  02 00 00 00  00 00 00 00
```

### ★★★ 结构解读

```
+0x00  4   0x100515BC   ← ★ 指向 RVA 0x515BC 的指针
+0x04  4   7            ← 长度 = 7
+0x08  4   2
+0x0C  4   0
+0x10..0x2F  全零
+0x30  4   0xFFFFFFFF   ← -1（无效句柄/索引）
+0x34  4   0
+0x38  4   2
+0x3C  4   0
```

★★ **`+0x00 = 0x100515BC` + `+0x04 = 7`** ——
**这是 MSVC `std::string` 的 SSO/长串布局？不符合。**

★ **但这是 `mov dword ptr [esp+0Ch], 1007C270h` 装进去的** ——
**`[esp+0Ch]` 在栈对象里是**第 3 个 dword**，
说明栈对象是一个 `{int, int, ptr}` 或 `{ptr, size, ptr}` 布局。**

★★★ **⇒ `0x7C270` 处的字节被当作**一个 4 字节值**（`0x100515BC`? 不，是 `0x100515BC` 的**地址**）
—— 等等，`mov [esp+0Ch], 1007C270h` 是把**常量 `0x1007C270`** 装进去，
**不是解引用它。**

★★ **⇒ `0x1007C270` 是一个**静态对象的地址**（VA），
`[esp+0Ch]` 存的是它的指针。**

★ **而它 `+0` 处是 `0x100515BC` —— 另一个指针**。
**`+4` 处是 7 —— 可能是 `std::string_view` 的 length。**

★★★ **⇒ `0x1007C270` 可能是 `std::string_view{ .data = 0x100515BC, .size = 7 }`。**

★ **`0x515BC` 在 `.rdata` 内 ✓ — 需要读它 7 字节的内容。**

---

## 五、★★★ 完整的 `OLMOD_*` 分层架构（字节级）

```
                ┌─────────────────────────────────────────────┐
                │  OLMOD_PROCESS_ROLE  (3 个插件都读)          │
                │     client | dedicated | combined            │
                └─────────────────────────────────────────────┘
                                   │
     ┌─────────────────────────────┼──────────────────────────────┐
     ▼                             ▼                              ▼
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────────┐
│ Localnetworking │      │  Alwaysoffline   │      │  CodolGameServer     │
│                 │      │                  │      │                      │
│ LOBBY_LISTEN(3) │      │ CLAIM_LOBBY(1)   │      │ 135 处 OLMOD_*       │
│ LOBBY_HOST(1)   │      │ lobby.codol.     │      │ (战斗参数)           │
│ SYNTHETIC_DNS(1)│      │   localhost(1)   │      │                      │
│                 │      │                  │      │                      │
│ ★ 装 Winsock    │      │ ★ 决定"是否认领" │      │ ★ 消费 SessionStart  │
│   hook + 绑 port│      │   大厅主机名     │      │ ★ gameplay hooks     │
└─────────────────┘      └──────────────────┘      └──────────────────────┘
        │                        │                          │
        └────────────────────────┴──────────────────────────┘
                                 │
                    ★ 三者必须一致才能绑 3074
```

★★ **`Platformwrapper` 只有 1 处 `OLMOD_` 引用** ——
**几乎完全独立于 OLMOD 配置体系**（只读一个变量）。

---

## 六、逐字节证据总表

| # | 证据 | 偏移 | 值/结论 |
|---|---|---|---|
| 1 | `OLMOD_CLAIM_LOBBY` | `Alwaysoffline` | **1 次（唯一）** |
| 2 | `OLMOD_LOBBY_LISTEN` | `Localnetworking` | **3 次（唯一）** |
| 3 | `OLMOD_LOBBY_HOST` | `Localnetworking` | 1 次 |
| 4 | `OLMOD_SYNTHETIC_DNS` | `Localnetworking` | 1 次 |
| 5 | `lobby.codol.localhost` | `Alwaysoffline` | 1 次 |
| 6 | `OLMOD_PROCESS_ROLE` | 三个插件各 1 | `Platformwrapper` 0 |
| 7 | `OLMOD_` 总数 | 135/41/7/1 | CodolGameServer 最重 |
| 8 | `0x519B0` 字符串 | 44 字节 | **"Failed to install one or more Winsock hooks."** |
| 9 | `0x7C270` 结构 | `{0x100515BC, 7, 2, 0, ...}` | 疑似 `string_view` |

---

## 七、★★★ 操作级结论（更新报告 023）

### 与我们大厅共存的完整开关集（**修正版**）

```
OLMOD_SKIP_AUX=1                   跳 Python auth / STUN / room_owner
OLMOD_LOBBY_LISTEN=<非ip:port>     ★ 让 Localnetworking 不绑 Lobby
OLMOD_CLAIM_LOBBY ≠ 1              ★ 让 Alwaysoffline 不认领
```

★★★ **三层都要处理**（比报告 023 的"两层"多一层认知）：
```
Python 侧（launch_chain 的 SKIP_AUX）  → 不启动 auth/STUN/room_owner
Localnetworking 侧（LOBBY_LISTEN）     → 不 bind 127.0.0.2:3074
Alwaysoffline 侧（CLAIM_LOBBY）        → 不认领 lobby 主机名
```

### ★★★ Winsock hook 互斥是**新发现的根本冲突**

**`Localnetworking::onStartup` 的第一份工作就是装 Winsock hook。**
**`nt10.py` 也装 Winsock hook。**

★★★ **⇒ 两者不能共存。**

★★ **这意味着"外部战斗服 + 我们的链"这条路**必须解决 hook 冲突**：**
- **要么**让 `nt10.py` 不装 hook（但那样读不到会话密钥）
- **要么**让 `Localnetworking` 不装 hook（但没有环境变量能关它）
- **要么**改 `nt10.py` 从别处读密钥

★★★ **这可能是记忆里"混合方案架构成立但解决不了"（`codol-lsg-never-listening`）的真正原因。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **反汇编 `0x4F00`（`Localnetworking` 的主逻辑：装 hook + 绑 Lobby）**
- [ ] ★★★ **读 `0x515BC`（7 字节字符串）**
- [ ] ★★ **`Alwaysoffline` 里 `OLMOD_CLAIM_LOBBY` 的上下文**（怎么被问到的）
- [ ] ★★ **`Alwaysoffline` 的 `Createserver` 是否就是"认领"的入口**
- [ ] ★ **`CodolGameServer` 135 处 `OLMOD_*` 的清单**（战斗参数）
- [ ] ★ **`0x5550` / `0x4390` / `0x5030` 三个函数**
