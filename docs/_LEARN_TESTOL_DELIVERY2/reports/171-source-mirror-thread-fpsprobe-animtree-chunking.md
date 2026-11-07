# 171 · 镜像线程的启动语义、fps 探针、animtree 的分块 SEH 与硬件写断点

## 一、范围

本报告学习 **2 处实现**：

- `ClientCommandTrace.cpp` 598–749 行（**该文件完整读完**）
- `ClientAnimtreeHook.cpp` 100–240 行

## 二、镜像线程的启动：文件总换，线程只起一次

```cpp
if (PsRecording.exchange(true))
    return true;    // a thread is already running; it picks up the new file
std::thread(playerStateThread).detach();
```

**先开文件、写表头、重置三个计数器，再 exchange**。若已有线程在跑，exchange 返回 true，直接返回——**新线程不创建，但旧线程下一轮就会看到新的 `PsOutput`**。

`StartedAt` 的守卫：

```cpp
if (!StartedAt) StartedAt = GetTickCount();
```

**只在第一次设置**，所以重跑不会把时间基准重置。但命令追踪那边是**无条件** `StartedAt = GetTickCount()` —— 两处不一致，且镜像这边更对（时间列应保持单调）。

### 2.1 停止要等采样器注意到

```cpp
PsRecording.store(false);
Sleep(120);        // let the sampler notice before the file closes
```

`PsInterval` 默认 50，所以 120 ms 覆盖两轮多。**这是必要的**：如果采样线程正卡在 `fprintf` 里而主线程 `fclose`，就是 use-after-close。

对比命令追踪的 `stopClientCommandTrace`——那里**没有**这个等待，因为它不需要等任何线程（录制的钩子是同步的）。

## 三、状态字符串把"未解析"翻译成人话

```text
"N sample(s) with no cg (not in a match)"
```

而不是 "N unreadable"。**同一个计数在状态里被解释成它的语义**，看状态的人不需要知道 `cg` 是什么。

## 四、fps 探针：三个地址、直接写 dvar

```text
MaxFpsDvarPointerRva = 0x7258770   // dword_7658770  指向 dvar 的指针
FrameCounterRva      = 0x2F3A08C   // dword_333A08C  每次 Com_Frame ++
ConnectionStateRva   = 0x72446B0   // dword_76446B0
DvarIntValueOffset   = 12
```

`readDvar()` 是**两级解引用**：先读指针，再加 12 —— 与之前报告里 `dvar[3]` 是同一个偏移。

### 4.1 为什么不走 `Dvar_SetInt`

```cpp
// WRITE THE VALUE DIRECTLY RATHER THAN THROUGH Dvar_SetInt, because the question is what
// the LIMITER does with it, not whether the dvar setter clamps. Zero is inside the
// registered range either way.
if (set && maxfps) *maxfps = value;
```

即：**要测的是限制器的行为，不是设置器的钳制**。

### 4.2 采样窗口与计算

```cpp
window = sampleMs ? sampleMs : 3000;
startFrames = *counter; startTicks = GetTickCount64();
Sleep(window);
endFrames = *counter; elapsed = GetTickCount64() - startTicks;
frames = endFrames - startFrames;
fps = frames * 1000.0 / elapsed;
minMsec = now ? (1000u / now) : 1u;
```

`minMsec` 的 `1000u / now` 是**整数除法**——正是头文件里那条"200 → 5 ms"的直接复现。`now == 0` 时 `minMsec = 1`（零跳过限制器）。

### 4.3 输出行

```text
"fps-probe com_maxfps before=%u now=%u minMsec=%u | frames=%u over %llu ms = %.1f fps |
 connectionState=%u (Com_Frame clamps to 30 when this is neither 0 nor 10)"
```

括号里那句话是**把结论写进日志**：连接状态不是 0 或 10 时 `Com_Frame` 会钳到 30。这条让读日志的人不必回头查文档。

**注意：`startFpsProbe` 是 detached 线程 + `Sleep(window)`**，与头文件里"绝不在 bridge 的请求路径上"一致。

## 五、animtree 的第四、五、六层

### 5.1 记录消费者（12.149）

```text
sub_527B40(a1@eax = record, a2, a3)   —— 分派命令记录的【唯一】消费者
从 sub_5400B0 的 0x5401F7 调一次
    +4  type      +16 entity      +20 KEY      +48 flags
```

注释：

> **与其追哪个数组填充它们（12.116.3，仍未闭合），不如在记录被应用时读记录本身**：`+4 type / +16 entity / +20 KEY / +48 flags`。**那正是本服务器必须复现的东西。**

即：**从消费端读，而不是从生产端找**。

### 5.2 硬件写断点（12.153）

```text
静态搜索生产者无望 —— 仅 +0x14 就有 212 个候选，而基址是指针，所以偏移不指名任何东西。
改为：从消费者学到一条活体记录的地址，然后在它的 record+20 上下【硬件写断点】，
让写者自己现身。
```

实现要点：

```text
DR0 在【每个线程】上装（写者不必是我们的线程）
一个 vectored handler 记录 faulting EIP
第一次命中后就解除武装，所以这不会把游戏冲垮
单独 opt-in：CODOL_ANIMTREE_WRITE_WATCH=1
```

三个原子：`watchTarget` / `watchArmed` / `watchHits`。

### 5.3 三个 SEH 辅助函数（POD-only）

```text
readEntryCount(p, out)     读 *(uint32*)p
copyName(name, out, cap)   有界复制
readZones(out, cap, count) 读 zone 表
```

注释：

> **受保护读放在 POD-only 的辅助函数里。`__try` 不能出现在需要对象展开的函数里（C2712），所以 SEH 住在这里，`std::string` 的工作留在调用者那边。**

这是与 `guardedUpload` / `guardedLink` 完全相同的约束，第二次出现。

### 5.4 `readZones` 的两道界

```cpp
count = *(uint32*)(module + ZoneCountRva);
if (count > 256) return 0;
...
for (i = 0; i < count && used + 2 < cap; ++i) {
    n = table + ZoneStride*i + ZoneNameOffset;
    if (!*n) continue;
    if (used) out[used++] = ',';
    for (k = 0; k < 48 && n[k] && used + 1 < cap; ++k) out[used++] = n[k];
}
```

三道：**zone 数量 ≤256**、**输出缓冲剩余 ≥2**、**名字最多 48 字符**。

### 5.5 `scanChunk`：把一次 65536 项扫描切成块

这是一段极有价值的踩坑记录：

> **第一个版本在一个 `__try` 里扫 65536 项；在进程内那会跑出分配的末尾，而 fault 杀掉了整次遍历**，这就是第一次运行记录 `chain=unreadable` 的原因。**一个外部的 `ReadProcessMemory` 探针在同样的 bug 下能活下来，因为它的读是逐次失败的而不是 faulting 的。**
>
> **分块意味着一次 fault 结束的是【扫描】，不是【函数】。**

即：**进程内 SEH 与外部 RPM 的失效粒度不同**——前者整函数，后者单次调用。这是"同一种 bug 在两种观测方式下表现不同"的又一个实例。

## 六、关键结论

1. **文件可换、线程只起一次**：`exchange(true)` 之后旧线程下一轮自然看到新文件。
2. **停止采样要等一轮**，否则 `fclose` 与 `fprintf` 竞争。
3. **要测限制器就直接写 dvar**，不经过会钳制的设置器。
4. **从消费端读，不从生产端找**：212 个候选 + 指针基址让静态搜索无望。
5. **SEH 的失效粒度是函数**，所以长扫描必须分块；外部 RPM 不需要，因为它的失效是逐次调用的。
6. **日志里可以写结论**（"Com_Frame clamps to 30 when this is neither 0 nor 10"）。

## 七、未闭合点

- `sub_5400B0` 用哪个数组填充命令记录（12.116.3）仍未闭合——写断点正是为了绕开它。
- animtree 的 519 vs 123 归因仍未在本组看到结论。
