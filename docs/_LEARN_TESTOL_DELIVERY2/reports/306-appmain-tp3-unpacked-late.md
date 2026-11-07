# 306 · **`.tp3` 未解包 ⇒ t~0 读密文**、`4065 ms` 的窗口、三个采集点 567/1055/2068/4065/8060

## 一、范围

本报告学习 `Appmain.cpp` 7780–8080 行。

## 二、`client-slot` 的**十四个字段**

```php
ingressStateKey =
    "xuid=" + xuid + " name=" + name + " state=" + state +
    " profile=" + receivedMask + "/" + requiredMask +
    " profile_complete=" + (0|1) +
    " gamestate_stage=" + stage + " gamestate_msg=" + msgNum +
    " session_generation=" + gen + " generation_active=" + (0|1) +
    " gameplay=" + state + " loadout_seq=" + seq + " pending_loadout_seq=" + seq +
    " team=" + team + " pending_team=" + team;
```

### 2.1 十四个

```text
xuid / name / state
profile（两个掩码）
profile_complete
gamestate_stage / gamestate_msg
session_generation / generation_active
gameplay
loadout_seq / pending_loadout_seq
team / pending_team
```

### 2.2 而 `ingressStateKey` 被**单独存**以便变化检测

```cpp
if (LastLoggedClientIngressState[clientNum] != ingressStateKey)
{
    logGameServer("client-slot " + clientNum + " " + ingressStateKey + " msg_ack=" + ... + " reliable_ack=" + ...);
    LastLoggedClientIngressState[clientNum] = ingressStateKey;
}
else { /* 无变化 */ }
else（ingress 不存在）{ LastLoggedClientIngressState[clientNum].clear(); }
```

**⇒ 三层**：

```text
变了     ⇒ 打印（含两个 ack）
没变     ⇒ 不打印
无 ingress ⇒ 清空
```

**⚠ 注意 `msg_ack` 与 `reliable_ack` **不在** `ingressStateKey` 里。**

**⇒ 所以它们变化**不会**触发打印。**

**⚠ 而它们是**最重要的进度指标**（ack 涨 = 客户端在推进）。**

**⇒ 但 §306 后面的 `runtime ... acks=` 会报它们（每 5 秒）。**

**✓ 所以不丢，但粒度粗。**

## 三、`client-packet-reject` 的**九个字段**

```cpp
rejectState =
    "sequence=" + seq + " ack=" + ack + " reliable_ack=" + reliableAck +
    " decoded=" + decodedCommandsSize + " rejected_cmd=" + rejectedCommandTime +
    " baseline_cmd=" + rejectedCommandBaselineTime + " reason=" + reason;
```

**⇒ 七个。**

### 3.1 而 `baseline_cmd` 是**关键**

**"`rejectedCommandBaselineTime`"** —— 所以拒绝时有**一个基线 commandTime**。

**⇒ 与记忆里"`packet-omit baseline must be `MSG_SetDefaultUserCmd` not previous packet (Wetwork turret intro failure)"**相关。**

**✅ 跨报告联系。**

## 四、`runtime` 的**九个量**

```php
"runtime clients=" + connected + " active=" + active +
" packets=" + received + " dropped=" + dropped +
" snapshots=" + sent + " frameReject=" + name + ":" + count +
" socketError=" + err + acknowledgeProgress
```

### 4.1 八个 + acks

```text
clients / active
packets / dropped
snapshots
frameReject（名字 + 计数）
socketError
acks（每客户端）
```

### 4.2 而 `statusChanged` 的**六项**

```cpp
connectedClients != last
activeClients != last
netchanPacketsReceived != last
snapshotMessagesSent != last
worldFrameRejections != last
lastSocketError != last
```

**⇒ 六项。**

### 4.3 而**5 秒节流**

```cpp
if (statusChanged && (!LastRuntimeStatusLogMilliseconds ||
    nowMilliseconds - LastRuntimeStatusLogMilliseconds >= 5000))
```

**⇒ 两层**：

```text
状态变了
且距上次 >= 5 秒
```

**✓ 与 §279 的 1 秒节流不同（这里 5 秒）。**

**⚠ 所以"状态变了"不会立即打印 —— 最多延迟 5 秒。**

## 五、`runtime-perf` 的**四个外层 + 每客户端七个**

```php
"runtime-perf tickUs=" + formatTimingWindow(serverTiming) +
" sendUs=" + formatTimingWindow(sendTiming) + clientFlow
```

### 5.1 而 `clientFlow` 的每客户端**七个量**

```cpp
clientFlow += clientNum + "{pending=" + pendingUserCmdCount +
    " cmdAge=" + commandAge +
    " recvExec=" + receivedExecutedGap +
    " ackGap=" + acknowledgeGap +
    " snapBuild=" + name + ":" + attempts + "/" + failures +
    " snapUs=" + formatTimingWindow(snapshotTiming[clientNum]) + "}";
```

**⇒ 七个（含 `snapBuild` 的三部分）。**

### 5.2 而**三个推导的年龄/间隔**

```cpp
commandAge   = serverTime - lastExecutedUserCmdTime      （-1 若无）
recvExec     = lastReceivedUserCmdTime - lastExecutedUserCmdTime   （-1 若无）
ackGap       = outgoingSequence - messageAcknowledge      （UINT32_MAX 若无）
```

**⇒ 三个，且**都有哨兵**（`-1` 或 `UINT32_MAX`）。**

**✅ 与 §278 的 `optionalClient`（`0xFFFFFFFF`）同族（第八次"用不可能的值作哨兵"）。**

### 5.3 **`commandAge` 是最重要的一个**

**⇒ "最后一个执行的 usercmd 有多老"** —— 所以如果它持续增长 ⇒ **客户端卡了。**

**✅ 与 §278 的"六个 usercmd 时间点"配合。**

### 5.4 而 `recvExec` **为负**是正常的

**⇒ 因为 `lastReceived` 通常**晚于** `lastExecuted`（收到但还没执行）。**

**⚠ 如果为**正** ⇒ 执行了比收到的更新的 ⇒ **异常**。**

**✓ 所以这个数的符号有诊断意义。**

### 5.5 而 `ackGap` 是**未确认的包数**

**⇒ 如果持续增长 ⇒ **客户端不 ack 了**。**

**✅ 与 §278 的 `messageAcknowledge` 配合。**

## 六、`runtime-frame` 的**七个**

```cpp
"runtime-frame fixedUs=" + frameTiming.total +
" prepareUs=" + frameTiming.prepare +
" beginUs=" + frameTiming.beginWorld +
" thinkUs=" + frameTiming.clientThink +
" thinkCommands=" + frameTiming.clientThinkCommands +
" modeUs=" + frameTiming.mode +
" endUs=" + frameTiming.endAndPublish
```

### 6.1 六个阶段 + 一个计数

```text
total / prepare / beginWorld / clientThink / mode / endAndPublish
clientThinkCommands
```

### 6.2 而**六个阶段**

```text
prepare        准备
beginWorld     开始世界
clientThink    【客户端 think】
mode           模式
endAndPublish  结束与发布
```

**⇒ 而 §263 说"`section 103d put 50 ms of a 63 ms frame in clientThink`"。**

**⇒ 所以 `thinkUs` 是**那个 50 ms** 的位置。**

**✅ 跨报告闭环。**

## 七、**`.tp3` 未解包 ⇒ t~0 读密文**（本组最重要的一段）

### 7.1 那段完整的发现

```php
// LOCAL OVERRIDE (olmod-local, 2026-10-03) -- .tp3 UNPACK ORDER.
//
// Measured on codoMP_client_shipRetail.exe
// SHA256 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537:
// the plugin's entry callbacks run at t~0 while the main image is still
// packed, so installDedicatedProcessPatches() reads ciphertext at RVA
// 0x0037EE5A (`02 2E 08 00 AF 04 ...`, not `81 3D C0 80 1F 0E ... 75 2D`)
// and Bindings.bind() reports "native entity binding prefix mismatch
// function=SV_LinkEntity" against RVA 0x0034EF10. Both RVAs read correctly
// from t=4065 ms onwards (sampled 567/1055/2068/4065/8060 ms). Upstream's
// out.exe is an already-unpacked image, which is why upstream never saw it.
//
// So do not fail at t~0: wait for the unpack on a worker thread, then run
// the real startup exactly once. The wait must NOT happen on this thread --
// the packer runs on the game's main thread and blocking here would stop it.
```

### 7.2 九层

```text
1. **`.tp3` 解包顺序** —— 本地覆盖，2026-10-03
2. 在 `codoMP_client_shipRetail.exe` 上测量，SHA256 **36997674...172B537**
3. ⇒ 插件的入口回调在 **t~0** 跑而**主映像仍然是被打包的**
4. ⇒ `installDedicatedProcessPatches()` 在 RVA **`0x0037EE5A`** 读到**密文**
     实测 `02 2E 08 00 AF 04 ...`（而不是 `81 3D C0 80 1F 0E ... 75 2D`）
5. ⇒ 而 `Bindings.bind()` 报 "native entity binding prefix mismatch
     function=SV_LinkEntity" 对着 RVA **`0x0034EF10`**
6. ⇒ **两个 RVA 从 t=4065 ms 起才读对**（采样 **567/1055/2068/4065/8060 ms**）
7. ⇒ **上游的 `out.exe` 是一个已解包的映像** ⇒ **这就是为什么上游从没见过它**
8. ⇒ 所以**不要在 t~0 失败**：在**工作线程上等解包**，然后**精确地跑一次**真正的启动
9. ⇒ **等待绝不能在【这个】线程上发生 —— 打包器在游戏主线程上跑，阻塞在这里会停住它**
```

### 7.3 五个采样点的**精确读数**

```text
567 ms    ✗ 密文
1055 ms   ✗ 密文
2068 ms   ✗ 密文
4065 ms   ✓ 正确
8060 ms   ✓ 正确
```

**⇒ 所以解包发生在 **2068 到 4065 ms** 之间。**

**✅ 一个干净的二分区间的测量。**

### 7.4 而两个 `0x0037EE5A` 与 `0x0034EF10`

**⇒ 两个 RVA：**

```text
0x0037EE5A   installDedicatedProcessPatches 的补丁点
0x0034EF10   SV_LinkEntity（Bindings.bind 的前缀守卫）
```

**✅ 两个独立的症状指向同一个原因。**

### 7.5 而"**上游从没见过它**"

**⇒ 三层**：

```text
1. 上游的 `out.exe` 是**已解包**的
2. ⇒ 所以它在 t~0 就能读对
3. ⇒ **上游永远看不到这个时序问题**
```

**✅ 与 §283 的"本机客户端虚拟空间 ~1998 MB"同族**（本机与上游的**环境差异**）。**

**⇒ 第四次"上游与我们的环境不同"。**

### 7.6 而**"等待绝不能在【这个】线程上"**

**⇒ 五层**：

```text
1. 等待**绝不能**在这个线程上
2. 因为**打包器在游戏主线程上跑**
3. ⇒ **阻塞在这里会停住它**
4. ⇒ 而一个停住的打包器 ⇒ **永不完成**
5. ⇒ **死锁**
```

**✅ 这是一个**致命的**并发约束 —— 与 §282 的"在这里等就绪 = 死锁"**完全同族**（第二次）。**

## 八、`initialize()` 的**三项前置**

```cpp
void initialize()
{
    const std::lock_guard lock(StartupMutex);
    if (Installed) return;                                    // ① 幂等
    if (!CodolGameServer::startupImageUnpacked())             // ② 未解包
    {
        scheduleDeferredInitialize();
        return;
    }
    const auto role = OlMod::processRole();
    ...
}
```

### 8.1 三层

```text
① `Installed` ⇒ 直接返回（幂等）
② 未解包 ⇒ 安排延迟初始化并**返回**
③ 已解包 ⇒ 真正初始化
```

### 8.2 ⚠ **`Installed` 在延迟路径上**不**置真**

**⇒ 所以 `initialize()` 会**反复被调用**（每次 `scheduleDeferredInitialize` 之前）。**

**⚠ 而 `scheduleDeferredInitialize` 可能自己幂等。**

**⇒ 待读。**

## 九、`UnsignedFastfilePatch` 的**三项**

```cpp
// A custom zone can be requested before the frame hook exists. Apply
// the explicit unsigned-fastfile opt-in at the plugin's earliest entry
// for both client and dedicated processes.
if (!UnsignedFastfilePatchAttempted)
{
    UnsignedFastfilePatchAttempted = true;
    UnsignedFastfilePatch = installUnsignedFastfilePatch();
    if (*UnsignedFastfilePatch != NotRequested) { logGameServer(...); }
}
```

### 9.1 三层

```text
1. **一个自定义 zone 可以在帧钩子存在之前被请求**
2. ⇒ 在插件的**最早入口**应用无签名 fastfile 的显式 opt-in，**客户端与专用服都做**
3. ⇒ 一次性（`Attempted`）
```

**✅ 与 §275 的 `ClientProcessPatchAttempted` 同族（第五次"attempted 一次性"）。**

## 十、关键结论

1. **`client-slot` 的十四个字段**，但 **`msg_ack`/`reliable_ack` 不在变化键里**（只在 5 秒的 `runtime` 里）。
2. **`client-packet-reject` 的七个字段含 `baseline_cmd`** —— 与记忆里 packet-omit 基线问题相关。
3. **`runtime` 的八个量 + acks**，而 `statusChanged` 六项 + 5 秒节流 ⇒ **最多延迟 5 秒**。
4. **`runtime-perf` 的每客户端七个量**，含三个推导的年龄/间隔（都有哨兵）。
5. **`commandAge` 持续增长 ⇒ 客户端卡了**。
6. **`recvExec` 为负正常，为正在异常**。
7. **`ackGap` 持续增长 ⇒ 客户端不 ack**。
8. **`runtime-frame` 的六阶段含 `clientThink`** —— 就是 §263 的 50 ms/63 ms 的位置。
9. **⭐ `.tp3` 未解包 ⇒ t~0 读密文** —— 两个 RVA（`0x0037EE5A`、`0x0034EF10`）都读到密文。
10. **五个采样点 567/1055/2068/4065/8060** ⇒ 解包发生在 2068 到 4065 ms 之间。
11. **"上游的 `out.exe` 是已解包的映像 ⇒ 这就是为什么上游从没见过它"** —— 环境差异第四次。
12. **"等待绝不能在【这个】线程上，因为打包器在游戏主线程上跑"** —— 与 §282 的死锁同族（第二次）。
13. **`initialize()` 的三项前置**，而 `Installed` 在延迟路径上不置真。
14. **`UnsignedFastfilePatch` 在最早入口应用**（"attempted 一次性"第五次）。

## 十一、未闭合点

- `scheduleDeferredInitialize` 的幂等性。
- `rejectedCommandBaselineTime` 的确切语义。
- `.tp3` 解包的确切时刻（2068–4065 之间）。
- `Appmain.cpp` 8080 行之后未读取。
