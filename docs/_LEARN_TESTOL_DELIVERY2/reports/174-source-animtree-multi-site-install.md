# 174 · 六个钩子的分层安装与 rel32 目标校验

## 一、范围

本报告学习 `ClientAnimtreeHook.cpp` 660–899 行（**该文件在本组读取范围内完整**）。

## 二、`resolveHook` 的最终日志行

```text
ANIMTREERESOLVE n=<序号> name=<名字|"<unreadable>"|"<null>">
    -> 0x<指针> entries=<N|"unreadable"> zones=<N|"?"> [<zone 列表>] <chain 或 "chain=unreadable">
```

一行里同时给出：

- **名字**（三级区分）；
- **返回指针**；
- **条目数**；
- **已加载 zone 数与列表**；
- **字符串表链遍历结果**。

设计意图很清楚：**一次解析的全部上下文在一行里**，因为下一次同名字的解析可能要等下一张地图。

## 三、两层环境开关

```text
CODOL_ANIMTREE_RESOLVE_HOOK   控制【是否安装】
CODOL_ANIMTREE_TRACE          控制【是否装诊断型钩子】
```

注释说明了分层理由：

> **下面的 resolver/build/populate 钩子是生产修复。allocator 与 record-consumer 钩子是旧的逆向仪器**：每一个都在动画热路径上加一个 thunk、一个原子和一个格式化文件写，**恰好在僵尸潮出现时产生几千条事件**。**保留这些仪器可用，但普通游玩时绝不安装它们。**

即：**生产修复与逆向仪器分开授权**。

`CODOL_ANIMTREE_RESOLVE_HOOK` 的默认关理由：

> **本会话里两个改动早先弄坏过客户端（12.127、12.131）**；一个重写客户端自己加载路径的补丁**显式 opt-in 而不是出厂启用**。

## 四、六个钩子的安装顺序与独立性

### 4.1 第一个：resolve（**唯一硬要求**）

```text
PE 头两级校验（MZ / PE\0\0）
ResolveCallRva + 5 > imageSize || ResolveRva >= imageSize → UnsupportedHost
验 5 字节 → 不符则 UnexpectedBytes 并【整个函数返回】
originalResolve = module + ResolveRva
打补丁
```

**只有这一个失败会让整个安装返回 `UnsupportedHost` / `UnexpectedBytes`。**

### 4.2 后五个：**各自独立校验，失败只跳过自己**

```cpp
// AND THE BUILD SITE. Verified independently; if its bytes do not match the
// resolve hook still stands, because the two answer different questions.
```

每一项的结构都是：

```text
if (基址 + 5 <= imageSize && 目标 < imageSize && 字节相符) {
    originalX = module + XRva;
    打补丁
}
```

**没有 else，没有错误返回** —— 因为"build 钩子装不上"不影响"resolve 钩子已经装好"。

这是"多站点补丁"的正确形状：**每个站点独立验证、独立安装、互不牵连**。

### 4.3 五个 alloc 站点：额外校验 **rel32 目标**

```cpp
if (site[0] != 0xE8) continue;                                   // 必须是 call
memcpy(&rel, site + 1, 4);
target = (uintptr_t)site + 5 + rel;
if (target != originalAlloc) continue;                            // 必须是【同一个】目标
```

注释：

> **每一个在被触碰前都验证它是一个 `E8` 且它的 rel32 真的指向 `sub_788540`**，所以一个错误的偏移会**拒绝**而不是把别的什么东西重定向。

这比"验原字节"更强：**验的是"这条 call 真的调到我们想的那个函数"**，而不只是"这里的字节长得对"。

`applyThunk` 的 `ApplyCallRva` 站点也是同样的 rel32 目标校验。

## 五、rel32 计算的统一模式

六处都是同一段：

```cpp
target = (uintptr_t)&hook;
next   = (uintptr_t)site + 5;
relative = (int32)(target - next);
std::array<uint8_t,5> replacement{ 0xE8 };
memcpy(replacement.data()+1, &relative, 4);

DWORD old{};
if (VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &old)) {
    copy(replacement, site);
    FlushInstructionCache(GetCurrentProcess(), site, 5);
    DWORD ignored{};
    VirtualProtect(site, 5, old, &ignored);
}
```

**注意 `VirtualProtect` 恢复在 `FlushInstructionCache` 之后**（与 `FrameHook.cpp` 相同，与 `ClientCommandTrace.cpp` 相同，与 `DisconnectWitness.cpp` 也相同——全项目一致）。

## 六、"安装完成"的语义

```cpp
installed.store(true);
return AnimtreeHookResult::Installed;
```

**只要 resolve 站点成功就返回 `Installed`**，即使后面五个都没装上。这个语义诚实但需要在日志里能看出来——而每个跳过都是**静默的**（没有日志）。

**这是一个可以指出的不足**：`Installed` 不能区分"六个全装"与"只装了第一个"。

## 七、`animtreeHookResultName`

```cpp
Installed → "installed"
AlreadyInstalled → "already installed"
...（本组读到 899 行，其余未读全）
```

小写字符串，与 `DisconnectWitness` 的 `disconnectWitnessResultName` 风格一致。

## 八、关键结论

1. **生产修复与逆向仪器分层授权**（两个环境变量），因为诊断钩子在热路径上会产生几千条事件。
2. **多站点补丁要独立校验、独立安装**：一个站点字节不符不影响其他站点。
3. **验 rel32 目标比验字节更强**：确认"这条 call 真的调到我们想的函数"。
4. **`Installed` 语义过于宽泛**：不能区分"全装"与"只装了主站点"。
5. **全项目一致的补丁顺序**：`VirtualProtect` → 写 → `FlushInstructionCache` → 恢复保护。

## 九、未闭合点

- 519 vs 123 的归因结论仍未在本组出现（钩子已就位，结果在别处）。
- `sub_5400B0` 的记录来源仍未闭合。
- `Installed` 不反映实际装了几个站点。
