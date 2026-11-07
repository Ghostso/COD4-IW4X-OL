# 学习报告 010 — launch_chain.py 的 chain_env 深度解析（行 150-187）

**学习范围**：`chain_env()` 全部环境变量及其背后的实测依据
**核心发现**：确认了不含 `NT10_INJECT`，报告 009 结论成立

---

## 一、九个环境变量全表

| 变量 | 值 | 谁消费 | 依据 |
|---|---|---|---|
| `OLMOD_PROCESS_ROLE` | `combined` 或 `client` | 插件 | `CodolGame.py:297-319` |
| `OLMOD_DEDICATED_CONTROL_PORT` | `28961` | dedicated | 同上 |
| `OLMOD_CLIENT_BRIDGE_PORT` | `28962` | 客户端桥 | 同上 |
| `OLMOD_ROOM_OWNER_PORT` | `28970` | room owner | 同上 |
| `OLMOD_CLIENT_INSTANCE` | `1` | 插件 | 同上 |
| `OLMOD_CLAIM_LOBBY` | `1` | **Alwaysoffline** | ★ 见下 |
| `OLMOD_CONSOLE_LOG` | 默认 `0` | 插件日志 | 见下 |
| `CODOL_FORCE_RECORD_VALIDATOR` | `1` | CodolGameServer | ★ 见下 |
| `OLMOD_STATS_NAME_UTF8` | `1` | Stats/Friends2 | 见下 |

★ **没有 `NT10_INJECT`。** 这一条直接坐实报告 009。

---

## 二、`OLMOD_CLAIM_LOBBY=1` —— 最关键的一个（行 157）

注释引用了 `CodolGame.py:311-314` 原文：

> route `lobby.codol.localhost` to **this process's own backend** instead of
> the C# LobbyServer, so **MatchmakingService runs** and can send `ConfigureSession`
> to the game server. Without it `QueryEndpoint` reports
> `sessionConfigured=false / bound=false` and **no match can start**.

### 机制拆解

```cpp
// Servers.cpp:109-116
if (contains(value, "lobby.codol.localhost"))
{
    const auto size = GetEnvironmentVariableA("OLMOD_CLAIM_LOBBY", claim, ...);
    const auto enabled = size == 1 && claim[0] == '1';
    return enabled ? ServerKind::lobby : ServerKind::none;
}
```

**`ALWAYSOFFLINE` 认领 `lobby.codol.localhost` 这个主机名的条件就是 `OLMOD_CLAIM_LOBBY=1`。**

★ **这是"谁管大厅"的总开关**：
- `=1`：本进程（插件）管大厅
- `≠1`：不认领，让别的服务（C# LobbyServer / Python lobby）管

★★ **这与 GOLDEN 链的冲突点就在这里**：GOLDEN 用独立的 `lobby_server.py`，
如果插件也设 `OLMOD_CLAIM_LOBBY=1`，**两边都声称管大厅**，必然冲突。

---

## 三、`OLMOD_CONSOLE_LOG` 的完整来龙去脉（行 158-174）

### 第一版：硬编码 `"1"`

### 问题（2026-10-12 实测）

> 每一行游戏服日志都是**同步写 CONOUT$**，`CodolGameServer.log` 自己测到了：
> - `LOGSTALL consoleDebugUs=28710` → **28.7 ms/行**
> - `consoleDebugUs=90836` → **90.8 ms/行**
>
> 按 ~18 行/秒算，帧线程大部分时间**阻塞在 WriteFile**，不是在计算。
> 帧遥测显示：`FRAMESTALL wallUs=50697..95377` 而 `threadCpuUs=0..46875` —— **阻塞，不是忙**。

### 改法

```python
env["OLMOD_CONSOLE_LOG"] = os.environ.get("OLMOD_CONSOLE_LOG", "0")
```

**默认 `0`，但外部显式值仍优先。**

### ★★ 作者的自我纠偏（行 169-173）—— 这一段最有价值

> **纠偏（第 61 轮实测，勿把本改动当结案）**：console 开关**尚未被证明**是
> "进图卡顿"主因 —— 甲方 14:16 那次（他称"流畅"）进程环境**仍是 `OLMOD_CONSOLE_LOG=1`**，
> 而 FRAMESTALL 与"**是否正在进图**"强相关：
> - 14:17/14:18 各 2 次（max 0.09s）
> - **14:19 进图 35 次（max 3.44s）**
> - 14:20 32 次（max 1.74s）
>
> **本改动只是"让干净对照成为默认"。**

**这是一个诚实的研究记录**：
- 最初以为 console 输出导致卡顿
- 实测发现"流畅"那轮 console 也是开的
- 真正相关的是"是否正在进图"
- 但改动保留（默认关 = 更干净的对照）

★ **学习价值**：作者没有把"看起来合理的因果"当成结论，而是**用对照实验证伪了自己**。

---

## 四、`CODOL_FORCE_RECORD_VALIDATOR=1`（行 175-181）

### 做什么

> 让进程内插件把**候选记录校验器** `sub_806F20`(RVA `0x406F20`) 改成 `mov al,1; ret 4`

### 为什么

> 于是客户端自己的成功路径跑起来：
> 容器状态 2 → 门写 `ctx+4=1` → `AllocResultHandler(ok=1)` →
> `server_index=0` → 进 `mmbook/mmstart`。

### ★ 关键：为什么不用 Frida

> **不再依赖 frida**（客户端虚拟空间 ~2 GB，注入进不去）。

★★ **这是一个重要的架构约束**：
客户端的**虚拟地址空间约 2 GB**（32 位进程上限），frida 注入失败。
所以所有内存修改都必须在**进程内插件**里做。

### 这个补丁的作用链

```
sub_806F20 是"候选记录校验器"（返回 1 = 通过）
        改成恒返回 1
            ↓
容器状态 2（校验通过）
            ↓
门写 ctx+4=1
            ↓
AllocResultHandler(ok=1)
            ↓
server_index = 0（从 -1 变成 0）
            ↓
进 mmbook / mmstart
```

★ **`server_index` 从 -1 变 0 是可观测判据**。

---

## 五、`OLMOD_STATS_NAME_UTF8=1`（行 182-186）

### 背景

> GBK 的 `Lifetime丷`(`81 52`) 在大厅生涯榜渲染成「▮R」= **逐字节回退**
> ⇒ 该渲染管线**不是 GBK 解码**。
> 假设它按 UTF-8 解：UTF-8 的 丷(`E4 B8 B7`) 应显示正确。

### 影响范围

> `StatsService`/`Friends2Service` 读这个键，**进程内 static 缓存，重启才生效**。

★ **"进程内 static 缓存"意味着**：改这个值必须重启客户端，热改无效。

---

## 六、`stop_all()` 的模式（行 190-197）

```python
ps("Get-Process codoMP_client_shipRetail ... | Stop-Process -Force")
ps("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
   "Where-Object { $_.CommandLine -match 'nt10|fake_auth|stun_local' } | ...")
ps("Get-Process ol_room_owner ... | Stop-Process -Force")
```

★ **三个层次**：
1. 按**进程名**杀客户端
2. 按**命令行正则**杀 Python 进程（避免误杀别的 Python）
3. 按**进程名**杀 room owner

★★ **注意它不杀 `launch_chain.py` 自己** —— 因为正在运行的就是它。

---

## 七、这一块的结论

1. **`chain_env` 不含 `NT10_INJECT`** ⇒ 报告 009 结论成立。
2. **`OLMOD_CLAIM_LOBBY=1` 是"谁管大厅"的总开关**，与 GOLDEN 的独立 lobby 冲突。
3. **`OLMOD_CONSOLE_LOG` 有一段完整的自我纠偏记录**，展示了诚实的研究方法。
4. **Frida 因 2GB 地址空间限制不可用**，所有内存修改必须在进程内插件做。
5. **`CODOL_FORCE_RECORD_VALIDATOR` 的作用链可观测**（`server_index` -1→0）。
6. **`OLMOD_STATS_NAME_UTF8` 有 static 缓存**，改后必须重启。

---

## 八、待验证

- [ ] `sub_806F20` 在本 build 是否仍在 RVA `0x406F20`
- [ ] `server_index` 的地址（注释说 `+0xE360`）
- [ ] `OLMOD_CLAIM_LOBBY` 不设时，大厅由谁提供
- [ ] `OLMOD_CONSOLE_LOG=0` 后日志还写不写到文件（还是完全不写）
