# 学习报告 002 — nt10.py 补丁机制（行 491-559）

**学习范围**：`parse_patches` / `apply_patches` / 四个兼容补丁的规格定义

---

## 一、补丁规格语法（行 491-493）

`patch_spec.txt` 里逗号分隔的每一项，两种形态：

| 形态 | 示例 | 解析结果 |
|---|---|---|
| **绝对地址** | `0x641654:9090` | `(0x641654, b'\x90\x90', ...)` |
| **模块:RVA** | `tenproxy.dll:0x7CAF:01` | `(('tenproxy.dll', 0x7CAF), b'\x01', ...)` |

`parse_patches` 的分支逻辑（行 502-506）：

```python
if parts[0].lower().startswith("0x"):
    out.append((int(parts[0], 0), bytes.fromhex("".join(parts[1:])), item))
else:
    out.append(((parts[0], int(parts[1], 0)), bytes.fromhex("".join(parts[2:])), item))
```

★ **`bytes.fromhex("".join(parts[1:]))` 这个写法**：把冒号后**所有**剩余段拼起来。
所以 `0x1234:90:90` 和 `0x1234:9090` 等价 —— 允许人为加冒号分段方便阅读。

★ **绝对地址的警告（行 492）**：「仅在自己早读到原始字节时才敢用」。
因为 `.tp3` 段运行时才解壳，绝对地址在解壳前后可能是不同内容。

---

## 二、`apply_patches` 的三重保险（行 512-543）

```python
before = rpm(h, addr, len(data))     # 写前读
if not wpm(h, addr, data): ...       # 写
after  = rpm(h, addr, len(data))     # 写后读
log(... "OK" if after == data else "!! 未生效")
```

**这是"不猜"原则的落地**：每次都打印 `写前 → 写后`，任何人看日志都能判断是否生效。

### 模块基址的等待逻辑（行 518-533）

```python
if not mb:
    tw = time.time()
    while time.time() - tw < 40:          # 最多等 40 秒
        ml2 = mods_peb(h) or ml
        mb = next((b for n, b, s in ml2 if n.lower().startswith(mod.lower())), 0)
        if mb: break
        time.sleep(0.3)
```

**为什么要等**：`TenProxy.dll` 到 t≈5s 才加载，而补丁规格可能在启动时就给了。
这里是"模块还没出现"的兜底。

★ 用的是 `mods_peb(h)` 而不是 toolhelp —— 因为 ACE 会封 toolhelp 枚举。

---

## 三、四个兼容补丁（行 546-557）—— 核心中的核心

**来源**：`CodolStateReader.cs` + `Run-Session.ps1`（三方实现）

| # | 名称 | 地址 | 模式 | 改动 |
|---|---|---|---|---|
| 1 | `PatchUnsignedAuthGate` | `0x00B9A78C` 前 16B 起 | `84 C0 74 B2 B0 01` | `74`(JE) → `75`(JNE) |
| 2 | `PatchUnsignedClientTicket` | `0x00B9A7B0` 起 | `84 C0 75 2A E8` | `75`(JNE) → `EB`(JMP) |
| 3 | `PatchAuthParseFallback` | `0x00B9A7B0` 起 | 某 `call` | 改成 `E9` 跳 `0x00B9A7F1` |
| 4 | `PatchLocalLsgNonceCheck` | `0x00BA3C1A` | `85 C0 75 44` | 在 `0x00BA3C1C` 写 `90 90` |

### 每个补丁的语义

**补丁 1**：`test al,al; je ...` → 改成 `jne`。
把"al==0 才跳过"变成"al!=0 才跳过"，**翻转了认证门的判断方向**。

**补丁 2**：`test al,al; jne ...` → `jmp`。
无条件跳过客户端票据校验。

**补丁 3**：把某个 `call` 改成 `jmp 0x00B9A7F1`。
**跳过整个解析函数**，直接落到 fallback 分支。

**补丁 4**：`cmp eax,eax`(即 `test`) 后跟 `jne 0x44`，把 JNE 的两个字节 NOP 掉。
即**无论 eax 是什么都往下走**，不校验本地 LSG 的 8 字节 challenge。

### 效果（注释原文）

> 客户端走"未签名"离线路径 —— 实测请求里的 `auth_task` 会**从 32 变成 10**（三方同款），
> 且**不再校验本地 LSG 的 8 字节 challenge**。

★ **`auth_task` 32→10 是可观测的判据**：日志里看到这个变化，就证明四个补丁都生效了。

---

## 四、最关键的一条：补丁必须等解壳

行 556-557：

> 这些字节在磁盘上是**加密的**(`.tp3` 段)，必须**运行时解壳后**才匹配得到，
> 所以照 `Run-Session.ps1` 的做法：**循环重试直到模式出现**。

```python
COMPAT_DEADLINE = 90.0    # 最长等 90 秒
```

**这就是为什么 `compat_patch_thread` 要跑 90 秒**：
- 启动瞬间读 `0xB9A78E`，得到的是**密文**，模式匹配失败
- 等 TP3 解壳（约 t≈2s 后完成，但机器不同可能更久）
- 解壳后才匹配得上

★ **由此可推出一个重要事实**：`.tp3` 段的内容**在运行时会被解密到内存**。
所以任何静态分析都必须用**运行时内存转储**，不能用磁盘文件。

---

## 五、地址核对的一个教训（行 552-553）

> 十进制 12205082 = `0xBA3C1A`，12205084 = `0xBA3C1C` —— **上次我误算成 `0xBA41DA`**；
> 用运行时转储 `n10ao_exe_lobby.bin` 核对：`85 C0 75 44` 确实在 `0xBA3C1A`

**这是作者自己记下的错误**：手算十六进制出错，导致一批无效实验。
**纠错方式**：用运行时转储的实际字节反查，而不是相信自己算的地址。

---

## 六、这一块的结论

1. **补丁规格支持两种寻址**：绝对地址（脆）和 模块+RVA（稳，跨 ASLR）。
2. **写前后都读**，日志里能直接看到 `before → after`，不靠猜。
3. **四个补丁的共同目标**：让客户端走**未签名离线路径**。
4. **可观测判据**：`auth_task` 从 32 变 10。
5. **必须等解壳**：`.tp3` 加密，磁盘态匹配不到，所以要 90 秒重试窗口。
6. **地址必须用运行时转储核对**，作者的 `0xBA41DA` 错误就是教训。

---

## 七、待验证

- [ ] 补丁 3 的原始 `call` 具体在哪个偏移（注释只说"某 call"）
- [ ] 四个补丁各自的**调用者函数名**（`PatchUnsignedAuthGate` 这些名字是三方起的）
- [ ] `auth_task` 32→10 在本 build 上是否仍成立
- [ ] `0xB9A7F1` 那个 fallback 分支实际做什么
