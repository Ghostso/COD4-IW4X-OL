# 279 · **十六个诊断命令**、`fps-set-<n>` 的"只能问作者想到的问题"、`1000/maxfps` + `Sleep(1)`

## 一、范围

本报告学习 `Appmain.cpp` 1928–2140 行。

## 二、`ensureClientSessionBridge` 的**三件事**

```php
if (ClientSessionBridge && ClientSessionBridge->running()) return;
if (!ClientSessionBridge) ClientSessionBridge = new OlMod::ClientSessionBridge();

static std::uint32_t lastAttemptMilliseconds{};
const auto now = GetTickCount();
if (lastAttemptMilliseconds && now - lastAttemptMilliseconds < 1000) return;
lastAttemptMilliseconds = now;
```

### 2.1 三层

```text
① 已在跑 ⇒ 返回
② 未创建 ⇒ `new`（永不 delete）
③ 【1 秒节流】
```

### 2.2 而 `new` 永不 `delete`

**⇒ 与 §271 的"插件在进程生命周期内保持加载，避免在 DLL 卸载时 join 控制线程（Windows loader lock 被持有）"一致。**

**⇒ 所以**故意泄漏**是为了避免 loader lock 死锁。**

### 2.3 而 1 秒节流是**只对启动尝试**

**⇒ 所以一个失败的启动每秒重试一次。**

**⇒ 而不是每帧。**

## 三、**诊断命令的完整清单**（本组最重要的一段）

### 3.1 十六个命令

```text
 1  item-names                    auditItemNames()           【线程】
 2  equipped-equipment            auditEquippedEquipment()   【线程】
 3  equipped-perks                auditEquippedPerks()       【线程】
 4  weapon-table                  auditWeaponItemsTable()    【线程】
 5  reward-table                  auditRewardTable()         【线程】
 6  alpha-barrett-templates       auditAlphaBarrettAssetTemplates()  【线程】
 7  unlock-coverage               reportUnlockAllCoverage()  【线程】
 8  trace-commands                installClientCommandTrace   【内联】
 9  trace-commands-stop           stopClientCommandTrace      【内联】
10  trace-commands-status         clientCommandTraceStatus    【内联】
11  trace-playerstate             installPlayerStateTrace     【内联】
12  trace-playerstate-stop        stopPlayerStateTrace        【内联】
13  trace-playerstate-status      playerStateTraceStatus      【内联】
14  fps                           startFpsProbe(false, 0)     【内联】
15  fps-uncap                     startFpsProbe(true, 0)      【内联】
16  fps-restore                   startFpsProbe(true, 200)    【内联】
17  fps-set-<n>                   startFpsProbe(true, n)      【内联】
```

**⇒ 十七个**（含 `fps-set-` 前缀）。

### 3.2 而 `equipped-equipment` 与 `equipped-perks` **不在未知命令列表里**

```php
return "unknown diagnostic '" + name + "'; known: item-names, weapon-table, "
    "reward-table, alpha-barrett-templates, unlock-coverage, trace-commands, "
    "trace-commands-stop, trace-commands-status, fps, fps-uncap, "
    "fps-restore, fps-set-<n>";
```

**⇒ 列表里**缺** `equipped-equipment` 与 `equipped-perks`（以及三个 `trace-playerstate*`）。**

**⚠ 这是一处遗漏** —— 用户查未知命令时会得到不完整的列表。

### 3.3 而七个**线程** vs 十个**内联**

### 3.4 那段

```php
// WHAT A DIAGNOSTIC CAN BE ASKED FOR, AND WHY IT ONLY STARTS THINGS.
//
// Each of these used to cost a full cycle -- rebuild, relaunch, and the player
// queueing up again -- to answer a question that is a loop over a table the
// running client already holds. They start on a detached thread and report to the
// log or a CSV; nothing is carried back over the bridge, so a slow audit can
// never hold up the capture path.
```

### 3.5 四层

```text
1. 每一个过去都要花【一整个周期】—— 重建、重启、玩家再排一次队
2. 只为回答一个"对运行中的客户端已持有的表做一次循环"的问题
3. ⇒ 它们在【detached 线程】上启动并报告到日志或 CSV
4. ⇒ 【什么都不通过桥带回来】，所以慢审计永远不会拖住捕获路径
```

**⇒ "只启动"（`it only starts things`）是关键设计。**

### 3.6 而"什么都不带回"意味着**返回值只是确认**

**⇒ 所以每个命令的返回值是一个**人类可读的开始确认**（含输出路径）。**

**✓ 一个正确的异步诊断接口。**

## 四、**`trace-commands` 与 `trace-playerstate` 为什么内联**

### 4.1 `trace-commands`

```php
// WATCH THE CLIENT DISPATCH EVERY RELIABLE COMMAND. Unlike the three above
// this one is not a sweep on a thread -- it patches a prologue and then
// records from whatever thread the engine dispatches on. So it runs INLINE
// here: a detached thread would report success before the patch existed, and
// "did the hook install" is the only question its reply can usefully answer.
```

**⇒ 四层**：

```text
1. 它不是线程上的扫描 —— 它【补丁一个序言】然后从引擎派发的线程记录
2. ⇒ 所以在【这里内联】跑
3. 因为 detached 线程会在补丁存在【之前】报告成功
4. 而"钩子装上了吗"是它的返回唯一能有用回答的问题
```

### 4.2 `trace-playerstate`

```php
// THE PLAYERSTATE MIRROR. Also inline, and for a different reason from the
// command trace: it starts a thread, and whether that thread STARTED is the
// only thing its reply can honestly report.
```

**⇒ 不同的理由**：

```text
trace-commands   【不启线程】，补丁本身必须同步确认
trace-playerstate 【启线程】，但"线程启动了吗"必须诚实报告
```

**✓ 两种内联的不同理由。**

## 五、**`com_maxfps` 的 `1000/maxfps` + `Sleep(1)`**（本组第二重要）

```php
// WHAT com_maxfps IS AND WHAT THE CLIENT ACTUALLY REACHES. The dvar is
// registered max=200, and Com_Frame's limiter is 1000/maxfps in INTEGER
// milliseconds plus Sleep(1), so 200 lands at ~186-190. Zero skips the
// limiter outright. These measure it instead of arguing about it.
```

### 5.1 四个数

```text
200           注册的最大值
1000/maxfps   限速器的【整数毫秒】
+ Sleep(1)    额外 1 毫秒
~186-190      实际达到的 fps
```

### 5.2 算术

```text
1000 / 200 = 5 ms（整数）
+ Sleep(1)  ⇒ 实际 ~6 ms（因为 Sleep 的粒度）
⇒ 1000 / 6 ≈ 166... 而实测 ~186-190
```

**⚠ 算术不完全闭合** —— 186-190 fps 对应 ~5.26-5.38 ms。**

**⇒ 所以 `Sleep(1)` 的实际开销不是整 1 ms**（因为 Windows 定时器精度）。

**⇒ 注释用"~186-190"给了**实测值**而不是推导值。**

**✓ 一个诚实的表述。**

### 5.3 而"零会直接跳过限速器"

**⇒ `com_maxfps = 0` ⇒ 无限制。**

**⇒ 与记忆里"`com_maxfps` ceiling is integer division + `Sleep(1)`"一致** ✓

## 六、**`fps-set-<n>` 的泛化教训**（本组第三重要）

### 6.1 那段自我批评

```php
// ANY VALUE, BECAUSE HARDCODING TWO OF THEM WAS THE MISTAKE. The first
// version of this probe shipped `fps-uncap` (0) and `fps-restore` (200)
// and nothing else, so the very next question -- "try 250" -- could not be
// answered without a rebuild and a cycle, on a tool whose entire purpose is
// trying values. A diagnostic that can only ask the questions its author
// already thought of is a worse instrument than one that takes an argument.
```

### 6.2 四层

```text
1. 第一版只发 `fps-uncap`(0) 与 `fps-restore`(200)
2. ⇒ 下一个问题"试 250"就无法回答，除非重建 + 一个周期
3. 【在一个整个目的就是"试值"的工具上】
4. ⇒ "一个只能问作者已经想到的问题的诊断，是一个比接受参数的工具更差的仪器"
```

### 6.3 那句方法论

**"A diagnostic that can only ask the questions its author already thought of is a worse instrument than one that takes an argument."**

**⇒ 这是本文件里**最重要的一句设计原则**之一。**

**⇒ 与 §252 的"转储全部 13 个候选偏移"（而不是猜 +8 再猜 +16）、§243 的"那这个表里到底有什么"同族。**

**⇒ 三次出现同一原则：**参数化 > 枚举作者预见的情况。****

### 6.4 `fps-set-<n>` 的解析

```php
const auto digits = name.substr(8);            // "fps-set-" 是 8 字符
uint32 requested{};
const auto *const first = digits.data();
const auto *const last = first + digits.size();
const auto parsed = std::from_chars(first, last, requested);
if (parsed.ec != std::errc{} || parsed.ptr != last || requested > 10000)
{
    return "fps-set-<n> needs a whole number 0..10000; 0 removes the limiter entirely";
}
```

### 6.5 三项

```text
from_chars 成功
全消费
<= 10000
```

**⇒ 第四项正确的 `from_chars` 用法。**

**⇒ 而 `"fps-set-"` 有 8 个字符 ⇒ `substr(8)`** ✓

### 6.6 而 `10000` 的上界

**⇒ 为什么是 10000？**

**⇒ 因为 `1000 / 10000 = 0` ms ⇒ 限速器失效 ⇒ 与 0 等价。**

**⇒ 所以 10000 是"实际无限制"的安全上限。**

**✓ 合理。**

## 七、`startFpsProbe` 的**三个参数**

```php
startFpsProbe(Bindings, /*setMaxFps*/ true, /*value*/ requested, /*durationMs*/ 3000)
```

### 7.1 三层

```text
bindings     引擎绑定
setMaxFps    是否设置 dvar（`fps` 命令是 false ⇒ 只测量不设）
value        dvar 值
durationMs   采样时长（3000 ms = 3 秒）
```

### 7.2 而 `fps`（不设）与 `fps-uncap`（设 0）

```text
fps          setMaxFps=false ⇒ 【只测当前值】
fps-uncap    setMaxFps=true, value=0 ⇒ 设 0 再测
```

**✓ 三个命令覆盖"只测 / 设 0 / 设 200"。**

## 八、`ensureDedicatedControlServer` 的**七个消息类型**

```php
if (message.type == ConfigureSession) { ... }
if (message.type == QueryEndpoint) { ... }
```

**⇒ 从这 140 行只看到两个。**

**⇒ 后续应该还有更多（待读）。**

### 8.1 `ConfigureSession` 的三步

```php
const auto descriptor = span((const uint8*)message.payload.data(), message.payload.size());
const auto configured = !descriptor.empty() &&
    Server.configureSessionDescriptor(descriptor) && Network.start();
if (configured) Server.setEnabled(true);
```

```text
① 描述符非空
② Server.configureSessionDescriptor(descriptor)
③ Network.start()
⇒ 三步全成 ⇒ setEnabled(true)
```

**⇒ 而 `&&` 短路 ⇒ 任一步失败就不再往下。**

### 8.2 而响应的两个字段

```php
return Response{
    .status = configured ? Accepted : Rejected,
    .payload = encodeEndpointStatus(dedicatedEndpointStatus()),
};
```

**⇒ 即使 `Rejected` 也带 payload** —— 所以调用者能看到**为什么**（端口/绑定状态）。

**✓ 一个好设计。**

### 8.3 而日志的三个量

```php
"ConfigureSession " + (configured ? "accepted" : "rejected") +
" bytes=" + descriptor.size() + " endpoint=" + endpoint.port
```

**⇒ 三个** —— 结果、字节数、端口。

### 8.4 `QueryEndpoint` 的**空载荷检查**

```php
if (message.type == QueryEndpoint)
{
    if (!message.payload.empty())
    {
        ...
```

**⇒ 所以 `QueryEndpoint` 不接受载荷。**

**⚠ 而这里只是"if 非空则..." —— 具体行为待读。**

## 九、关键结论

1. **诊断命令十七个**：七个线程 + 十个内联。
2. **未知命令列表缺 `equipped-equipment`/`equipped-perks`/三个 `trace-playerstate*`**。
3. **"只启动"是设计** —— 慢审计不拖住捕获路径。
4. **`trace-commands` 内联因为"detached 线程会在补丁存在之前报告成功"**。
5. **`trace-playerstate` 内联因为"线程启动了吗"必须诚实报告**。
6. **`com_maxfps` 的 `1000/maxfps` + `Sleep(1)` ⇒ 200 实测 ~186-190**。
7. **`0` 直接跳过限速器**。
8. **`fps-set-<n>` 的教训："只能问作者已想到的问题的诊断比接受参数的工具更差"** —— 本文件最重要的设计原则之一。
9. **这个原则第三次出现**（前两次：§252 的转储全部候选、§243 的"表里到底有什么"）。
10. **`fps-set-` 的 `substr(8)`** 与三项 `from_chars` 检查。
11. **`10000` 上界因为 `1000/10000 = 0`** ⇒ 等效于无限制。
12. **`ConfigureSession` 的三步 `&&`** 与"即使 Rejected 也带 payload"。
13. **`new` 永不 `delete`** —— 避免 DLL 卸载时的 loader lock 死锁。

## 十、未闭合点

- `ensureDedicatedControlServer` 的完整消息类型列表。
- 未知命令列表的遗漏是否有意。
- `startFpsProbe` 的实现（如何采样）。
- `Appmain.cpp` 2140 行之后未读取。
