# 学习报告 003 — nt10.py 四个兼容补丁的实际匹配逻辑（行 594-669）

**学习范围**：`_match_at` / `compat_patch_once` 的逐补丁实现

---

## 一、`_match_at` —— 支持"等价集合"的模式匹配（行 594-605）

```python
def _match_at(buf, off, pat):
    for j, p in enumerate(pat):
        if off + j >= len(buf): return False
        b = buf[off + j]
        if isinstance(p, (tuple, list, set)):
            if b not in p: return False
        elif b != p:
            return False
    return True
```

**核心设计**：pattern 元素可以是
- `int` —— 精确匹配
- `(tuple/list/set)` —— **等价集合**，命中任一即可

★ **为什么需要集合**：补丁 1 的模式是 `84 C0 (74|75) B2 B0 01`。
`74`/`75` 都可能出现（**已打过**或**没打过**），所以模式本身要兼容两种状态。

---

## 二、补丁 1：AuthGate（行 612-625）

```python
base = 0x00B9A78C - 16          # 往前 16 字节开始找
buf  = rpm(h, base, 40)          # 读 40 字节
for i in range(0, 40 - 6 + 1):   # 在 40 字节内滑动
    if _match_at(buf, i, (0x84, 0xC0, (0x74, 0x75), 0xB2, 0xB0, 0x01)):
        a = base + i + 2         # 要改的字节在模式 +2
```

**为什么从 `0xB9A78C-16` 开始找**：地址 `0xB9A78C` 是三方给的**参考点**，
但实际模式可能不在那个精确位置（版本差异），所以在 ±16 字节窗口内滑搜。

**为什么用 `84 C0 ... B2 B0 01` 六字节模式**：`84 C0` = `test al,al`，
但 `test al,al` 太常见，必须加上后面的 `B2 B0 01` 才唯一。

**幂等判断**：
```python
if cur == b"\x75": done.add(1)          # 已经是 JNE，跳过
elif cur == b"\x74" and _wpm_code(...): # 是 JE，改
```

★ **`b"\x75"` 和 `0x75` 的比较**：`rpm()` 返回 `bytes`，所以是 `bytes == bytes`。

---

## 三、补丁 2 与补丁 3 共用同一个采样窗口（行 627-658）

**这是本段最精妙的设计**：

```python
base2 = 0x00B9A7B0
buf2  = rpm(h, base2, 64)        # ← 只读一次，两个补丁共用
```

补丁 2 在 `buf2` 里找 `84 C0 (75|EB) 2A E8`
补丁 3 在**同一个 `buf2`** 里找 `E8/E9` + 12 字节模式

**为什么共用**：两者都在 `0xB9A7B0` 附近，一次读 64 字节覆盖两者，**减少一次跨进程读**。

但也带来一个**顺序依赖**（见报告 002 提到的 latch 问题）：
补丁 3 会把 `0xB9A7C7` 的 `E8` 改成 `E9`，
而补丁 2 的模式是 `84 C0 75 2A E8` —— **最后那个 `E8` 被改掉了**。

所以**补丁 2 必须在补丁 3 之前执行**。代码里恰好是这个顺序（2 在前，3 在后）。

---

## 四、补丁 3 的 12 字节模式（行 643）

```python
pat3 = (0x8D, 0x8D, 0x38, 0xFD, 0xFF, 0xFF, 0xC7, 0x85, 0x68, 0xFD, 0xFF, 0xFF)
```

反汇编解读：

```asm
8D 8D 38 FD FF FF    lea ecx, [ebp-0x2C8]
C7 85 68 FD FF FF .. mov dword [ebp-0x298], <imm32>
```

**这是一个 `lea` + `mov` 的组合**，作为 call 之后的"签名"。
用 `call` 目标不可靠（可能是不同函数），但**紧跟的这两条指令**是稳定的。

**改写方式**：
```python
rel = (0x00B9A7F1 - a - 5) & 0xFFFFFFFF
_wpm_code(h, a, b"\xE9" + struct.pack("<I", rel))
```

★ **`& 0xFFFFFFFF` 但 `struct.pack("<I")`**：rel32 是**无符号**打包，
但 CPU 会把它当**有符号**解释。若目标是往前跳，`rel` 会是负数，
实际算出 `0xFFFFxxxx`，CPU 解释为负偏移 —— **结果正确**，但写法容易误解。

---

## 五、补丁 4：最简单的那个（行 660-667）

```python
b4 = rpm(h, 0x00BA3C1A, 4)
if b4 == b"\x85\xC0\x90\x90":       # 已打过
    done.add(4)
elif b4 == b"\x85\xC0\x75\x44":     # 原始状态
    _wpm_code(h, 0x00BA3C1C, b"\x90\x90")   # 只改后两字节
```

```asm
85 C0        test eax, eax
75 44        jne  +0x44      →  90 90 (NOP NOP)
```

**NOP 掉 JNE = 无论 eax 是什么都往下走**。

★ 这里**没有滑搜**，直接读 `0xBA3C1A` 四字节。
因为补丁 4 是**绝对地址**且模式极短（4 字节），三方已验证过精确位置。

---

## 六、`_wpm_code` —— 写代码段的三步（行 574-591）

虽然这段在报告 001 区域附近，但它和补丁强相关，这里补齐：

```python
def _wpm_code(h, addr, data):
    ok, old = _vm_protect(h, addr, len(data))     # 1. 开写权限
    wrote   = wpm(h, addr, data)                   # 2. 写
    if ok: VirtualProtectEx(..., old)              # 3. 还原权限
    if wrote: FlushInstructionCache(h, addr, len)  # 4. 刷 icache ★
```

★★ **`FlushInstructionCache` 是关键**：
x86 虽然指令缓存与数据缓存一致，但 **Windows 要求显式刷新**，
否则另一个核上的执行可能读到旧指令。**不刷 = 补丁"看起来写进去了但没生效"**。

★ **`_vm_protect` 失败也照样试写**（`wrote = wpm(...)` 在 `if ok` 之外）：
因为有时目标页**本来就是 RWX**，`VirtualProtectEx` 返回 false 但写能成功。

---

## 七、这一块的结论

1. **滑搜 + 六字节模式**保证定位到正确位置，不依赖精确地址。
2. **幂等**：先判断是否已改过（`0x75` vs `0x74`），避免重复改坏。
3. **补丁 2 必须在补丁 3 之前**（共享 `buf2`，且补丁 3 会破坏补丁 2 的模式）。
4. **`FlushInstructionCache` 不可省**。
5. **补丁 3 的 `rel32` 无符号打包**是容易误解的写法，但结果正确。

---

## 八、待验证

- [ ] `pat3` 那 12 字节对应的完整函数（`lea ecx,[ebp-0x2C8]` 之后是什么）
- [ ] `0x00B9A7F1` 处是什么代码（fallback 分支的起点）
- [ ] 四个补丁的**执行顺序**是否真的如代码所示（2 先于 3）
- [ ] 补丁 4 的 `0xBA3C1A` 是否在 `.tp3` 段内（决定是否要等解壳）
