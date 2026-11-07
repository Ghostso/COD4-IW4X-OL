# 173 · DR 寄存器装配、naked thunk 的栈偏移、四个日志钩子

## 一、范围

本报告学习 `ClientAnimtreeHook.cpp` 440–660 行。

## 二、`armWriteWatch`：绝不挂起调用线程

### 2.1 那次死锁

```cpp
// NEVER THE CALLING THREAD. The first cut suspended every thread including this one
// and the process deadlocked instantly -- the client froze mid-demo (12.153). Our own
// debug registers are set without suspending, since a thread can safely set its own context.
if (te.th32ThreadID == GetCurrentThreadId())
    continue;
```

**排除自己**，末尾单独用 `GetCurrentThread()` + `Get/SetThreadContext` 给自己的线程装（**不挂起**，因为线程可以安全地设置自己的上下文）。

这是本组最实操的一条：**挂起所有线程包括自己 = 立即死锁**。

### 2.2 DR7 的位装配

```cpp
ctx.Dr0 = address;
ctx.Dr7 = (ctx.Dr7 & ~0xFul)         // 清 L0..L3 的本地启用位
        | 1ul                        // L0 启用（DR0 本地）
        | (0x1ul << 16)              // R/W0 = 01 = 只写
        | (0x3ul << 18);             // LEN0 = 11 = 4 字节
```

注释逐项写明：**`len=4 (0b11), rw=write (0b01), L0 enable`**。

关键细节：**先清 `Dr7 & ~0xF`** —— 清掉的是低 4 位的 L0..L3，**不是** RW/LEN 字段（那些在 16..31 位）。所以：

```text
bit 0      L0   DR0 本地启用
bit 16-17  R/W0  01 = 只在写时触发
bit 18-19  LEN0  11 = 4 字节
```

### 2.3 三态计数

```cpp
char buf[96];
snprintf(buf, sizeof(buf), "0x%08X on %d threads", address, armedCount);
```

`armedCount` **实际成功装上的线程数**——如果为 0，说明一个都没成功，日志会直接显示。

### 2.4 `watchArmed.exchange(true)` 的幂等

```cpp
if (watchArmed.exchange(true)) return;
```

第二次调用直接返回，不重复装配。

### 2.5 `AddVectoredExceptionHandler(1, watchVeh)`

第一个参数 **1 = first-chance**。所以单步异常在任何人看到之前先到这个处理函数。

## 三、`readRecord`：五个字段

```cpp
const auto *r = (const unsigned int*)record;
*type = r[1];    // +4
*ent  = r[4];    // +16
*key  = r[5];    // +20
*flags= r[12];   // +48
```

与头文件注释 `+4 type / +16 entity / +20 KEY / +48 flags` 逐项一致。

### 3.1 为什么 key 0 被跳过

```cpp
if (!key) return;    // key 0 dominates; only the rest matter
```

注释：

> **key 0 占主导；只有其余的重要。**

即：绝大多数记录是 key 0（正常情况），记录它们会淹没真正的异常。这与 `logNodeKey` 里 `if (key < 3) return;` 是同一个策略。

### 3.2 断点装在 `record + 20` 而非记录起点

```cpp
if (key > 2)
    armWriteWatch((uintptr_t)record + 20);
```

因为 `+20` 就是 **KEY 字段本身**——**谁的写让 key 变了，谁就是写者**。

## 四、两个 naked thunk 的栈偏移推导

### 4.1 `applyThunk`

```asm
pushad
pushfd
push eax              ; a1 = the record（入口 EAX）
call logApply
add  esp, 4
popfd
popad
jmp  [originalApply]
```

`pushad` 存而不清 EAX，所以 `push eax` 压的仍是入口值。

**注意顺序**：`pushad` 先、`pushfd` 后；恢复时 `popfd` 先、`popad` 后 —— 严格后进先出。

### 4.2 `nodeAllocThunk` 的偏移逐一验算

```asm
pushad                    ; 32 字节
pushfd                    ; 4 字节
mov ebx, [esp+36]         ; 返回地址
mov ecx, [esp+48]         ; a4 = parent
mov edx, [esp+44]         ; a3 = asset
push ebx                  ; caller
push ecx                  ; parent
push edx                  ; asset
push eax                  ; key
call logNodeKey
add  esp, 16
popfd
popad
jmp  [originalAlloc]
```

**验算**：

```text
入口时栈顶 = 返回地址（thunk 自己的返回槽）
pushad 后：[esp+32] = thunk 返回地址
pushfd 后：[esp+36] = thunk 返回地址          ⇒ [esp+36] 正确
          [esp+40] = a1
          [esp+44] = a2
          [esp+48] = a3
          [esp+52] = a4
```

但代码说 **`[esp+44] = a3 = asset`、`[esp+48] = a4 = parent`**。所以它的编号是：**`a1` 在 `[esp+40]`，`a2` 在 `[esp+44]`，`a3` 在 `[esp+48]`**，即**从 0 起编号且 a1 是第一个栈参数**。

而 `logNodeKey(key, asset, parent, caller)` 收到的是 `(eax, edx, ecx, ebx) = (key, [esp+44], [esp+48], [esp+36])`。压栈顺序 `ebx, ecx, edx, eax` 从右往左，所以：
- `caller` ← `ebx` = `[esp+36]`
- `parent` ← `ecx` = `[esp+48]`
- `asset`  ← `edx` = `[esp+44]`
- `key`    ← `eax`

**`add esp, 16` = 四个参数** ✓。

## 五、四个日志钩子

### 5.1 `populateHook`：先调原始，再测

```cpp
result = originalPopulate ? originalPopulate(name, a2, a3) : 0;
ordinal = populateOrdinal.fetch_add(1);
haveName = name && copyName(name, nameBuffer, 80);
snprintf(path, sizeof(path), "animtrees/%s.atr", haveName ? nameBuffer : "");
haveSize = haveName && readAssetSize(path, size) != 0;
log("ANIMTREEASSET n= name= assetSize= a3= ok=" + result);
```

**先调用原始函数**（这是所有透明钩子的共同纪律），再重做资产查找。

`haveName ? nameBuffer : "<unreadable>"` —— **可读性失败与空名区分**。

### 5.2 `buildHook`：记录构建结果

```cpp
result = originalBuild(name, a2, a3);
entries = result && readEntryCount(result, entries);
log("ANIMTREEBUILD n= name= a2= a3= -> 0x-------- entries=");
```

`haveEntries ? std::to_string(entries) : "unreadable"`。

这里 `name ? "<unreadable>" : "<null>"` —— **三级区分**：名字可读 / 指针非空但读不出 / 指针为空。

### 5.3 `resolveHook`：三个缓冲区

```text
nameBuffer[80]     名字
zoneBuffer[2048]   已加载 zone 列表
chainBuffer[1024]  链遍历结果
```

三个都开在栈上（固定大小），因为要在日志行里一次说完。

`readZones(...) != 0` —— 与 `readZones` 的返回约定一致（1 成功 / 0 失败）。

## 六、关键结论

1. **挂起所有线程包括自己是立即死锁**；自己的线程要单独用 context-set 而不挂起。
2. **DR7 的位装配要逐段说明**：`~0xF` 清 L0..L3、`1` 启 L0、`0x1<<16` 只写、`0x3<<18` 4 字节。
3. **断点装在 KEY 字段本身（`record+20`）**，因为"谁让 key 变了谁就是写者"。
4. **key 0 要跳过**，否则正常情况会淹没异常。
5. **naked thunk 的栈偏移必须验算**：`pushad(32) + pushfd(4)` 使 thunk 返回地址落在 `[esp+36]`。
6. **"读不出"与"空"要分三级**（`<unreadable>` / `<null>` / 实际值）。

## 七、未闭合点

- `resolveHook` 的日志行尾与最后一个钩子（`installClientAnimtreeHook`）未在本组读取。
- `sub_5400B0` 的记录来源仍未闭合；写断点正是绕开它的办法，但结果不在本组。
