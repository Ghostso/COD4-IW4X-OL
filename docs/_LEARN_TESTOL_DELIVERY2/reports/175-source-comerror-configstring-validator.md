# 175 · 断开见证（续）：Com_Error 钩子、configstring 校验器

## 一、范围

本报告学习 `DisconnectWitness.cpp` 80–199 行。

## 二、`comErrorHook`：入口钩子的返回地址偏移

```asm
pushfd
pushad
// Entry hook: [esp] held the return address, and pushfd(4) + pushad(32) put it at esp+36.
mov eax, [esp + 36]
push eax
call recordComError
add esp, 4
popad
popfd
jmp dword ptr [ComErrorTrampoline]
```

### 2.1 偏移验算

```text
入口：[esp+0] = 返回地址
pushfd 后（+4）：[esp+4] = 返回地址
pushad 后（+32）：[esp+36] = 返回地址    ✓
```

与 `nodeAllocThunk` 的 `[esp+36]` 完全一致——**同一个 36，因为同样的 `pushfd`+`pushad` 组合**。

### 2.2 与 `applyThunk` / `nodeAllocThunk` 的差别

`comErrorHook` 是**入口钩子**（偷的是函数开头的 5 字节），所以 `[esp+36]` 是**调用者的返回地址**。

而 `nodeAllocThunk` 是**call 重定向**（偷的是一条 `call` 指令），`[esp+36]` 同样是 thunk 的返回地址——两者数值含义相同（都指向"谁调了这里"），机制不同。

## 三、`recordDisconnect` 与 `recordComError` 的双重报告

两个函数结构完全相同：

```cpp
if (InterlockedExchange(&Reported, 1) != 0) return;      // 只报一次
line = "... called from 0x%08X (module+0x%X) -- resolve with Tools/olfinal/xrefs.py";
```

**两个独立的 `Reported` 变量**（`Reported` 与 `ComErrorReported`），所以 **CL_Disconnect 与 Com_Error 各自报一次**，互不抑制。

### 3.1 为什么都要

因为"客户端退出"可能是**正常的 `CL_Disconnect`**，也可能是 **`Com_Error` 崩溃**——而前面已经证明：

> `com_errorMessage` 为空**不等于** `Com_Error` 没跑。

## 四、configstring 校验器：一次拒绝一个索引

### 4.1 症状与定位

```text
sub_514540 是那个把 XBOXLIVE_CANTJOINSESSION 当作 ERR_SERVERDISCONNECT 抛出的函数
（实测：com_errorCode = 2 由 sub_4F82E0+0x11F 写入，调用者帧 sub_514540+0xA5）
```

反编译：

```text
mov  ebx, [ebp+8]            ← 一个 CONFIGSTRING 索引
cmp  ebx, 0x31D9             范围检查，否则在 +0x76 抛另一个
mov  al, [ebx + 0x77D8250]   它在 CCS 块里的 TYPE 字节
cmp  al, 0x17 / jae ok
cmp  al, 0x15 / je  ok
call sub_661610              CCS clear
push XBOXLIVE_CANTJOINSESSION / push 2 / raise
```

**判定规则**：`type >= 0x17` 或 `type == 0x15` 才通过，**否则清除并抛错**。

### 4.2 结论

> **所以它按索引拒绝【一个】configstring。记录那个索引就直接点它的名**——远好过猜哪个带出了问题。

这与之前报告里"`p <n>` 需要 type byte 为 21"是同一条 CCS 类型规则的另一面：**21 = 0x15**。

### 4.3 已排除的嫌疑

> **dmz loot 带是明显的嫌疑，而它已经被 `OLMOD_DMZ_LOOT_BAND=0` 跑过一次【排除】**：踢出照样发生，在 02:50:12。

### 4.4 又是六字节

```text
序言是 `55 8B EC 83 EC 10` —— push ebp / mov ebp,esp / SUB ESP,0x10
所以偷【六】字节，不是五。
五字节会把 `sub esp,0x10` 切成两半，【和今晚早些时候在 sub_77C290 上犯的同一个错误】。
```

**这是同一种错误在同一个晚上犯两次**——注释把它记下来，正是因为它是可重复的陷阱。

### 4.5 每一条都记，封顶 40

```cpp
// Every call is logged, capped -- the rejected one is not necessarily the first,
// and knowing which indices PASSED is as useful as the one that failed.
if (InterlockedIncrement(&ValidatorReported) > 40) return;
```

**这是与"只报一次"相反的策略**，理由明确：**通过的那些和失败的那个一样有用**。因为如果拒绝发生在第 N 次，前面 N-1 次通过的就是"正常范围"，能缩小嫌疑。

### 4.6 读出它即将测试的那个字节

```cpp
if (configString < 0x31D9)
    type = *(const uint8_t*)(base + (0x077D8250 - 0x00400000) + configString);
```

**用与它完全一样的方式读 type 字节**（同一个基址、同一个索引），所以日志里的 `typeByte` 就是函数看到的值，不是推断的。

### 4.7 日志格式

```text
"CS VALIDATE index=%u typeByte=0x%02X (accepts 0x15 or >=0x17) from module+0x%X"
```

**把接受条件写进日志** —— 读日志的人不需要回头查反汇编。

## 五、`validatorHook` 的两个参数

```asm
pushfd
pushad
// At entry [esp] is the return address and [esp+4] the first argument;
// after pushfd(4) + pushad(32) those sit at esp+36 and esp+40.
mov eax, [esp + 36]      ; 返回地址
push eax
mov eax, [esp + 44]      ; 第一个参数（原 [esp+40]）
push eax
call recordValidator
add esp, 8               ; 两个参数
popad
popfd
jmp dword ptr [ValidatorTrampoline]
```

**`[esp+44]` 是关键**：第一次 `push eax` 之后栈下移 4，原来的 `[esp+40]` 变成 `[esp+44]`。**注释显式写出了这个位移**，因为这是最容易算错的地方。

### 5.1 参数顺序

`recordValidator(configString, returnAddress)` —— 压栈顺序是"先返回地址、后 configString"，所以从右往左：`returnAddress` 先压、`configString` 后压。

等等——代码是 `push eax`（返回地址）**先**，然后 `push eax`（参数）**后**。栈是向下增长的，所以后压的在更低地址。

- 第一次 push（返回地址）→ 在较高地址
- 第二次 push（configString）→ 在较低地址 = 栈顶

`call` 时栈顶是最后一个 push，即 **configString 是第一个参数**。而签名是 `recordValidator(configString, returnAddress)` ✓。

## 六、关键结论

1. **`[esp+36]` 是 `pushfd(4) + pushad(32)` 之后的返回地址槽**，在四个不同的 thunk 里反复出现且数值相同。
2. **多次 push 后取后续参数要重算偏移**（`[esp+40]` → `[esp+44]`），注释显式记录了这个位移。
3. **`CL_Disconnect` 与 `Com_Error` 各自独立报一次**，因为退出可能来自任一路径。
4. **configstring 校验器按索引拒绝**，所以**记录索引就直接点名**；而"通过的那些"与"失败的那个"一样有用。
5. **六字节窃取是同一晚犯过两次的错**——`sub_77C290` 与 `sub_514540` 的序言都以 `sub esp, N` 结尾。
6. **可重复的陷阱要在代码里留名**（"the same mistake made on sub_77C290 earlier tonight"）。

## 七、未闭合点

- 到底哪个 configstring 索引被拒仍未点名（钩子已就位，结果不在本组）。
- dmz loot 带已排除；其余候选未在本组列出。
- `DisconnectWitness.cpp` 199 行之后的安装逻辑未读取。
