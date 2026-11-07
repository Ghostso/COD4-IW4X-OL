# 学习报告 024（重开）— `nt10.py` 嵌套结构 + 补丁机制

**学习范围**：`build_tas_image` 尾部（477–488）+ `parse_patches` / `apply_patches`（491–545）
**性质**：全实测
**★★★ 本报告揭示 TCLS 镜像的**第三套寻址（嵌套）**与**读-写-读**的补丁校验**

---

## 一、★★★★★ TCLS 镜像的**第三套命名空间**（嵌套结构）

### 1.1 结构还原（第 464–483 行）

```python
nested = rec                                     # key20 记录的起始
e1 = nested + 8                                  # 条目 E1 在 key20 记录之后 8 字节
struct.pack_into("<I", b, nested, e1)            # ★ key20 的 len 字段 = E1 偏移
struct.pack_into("<I", b, nested + 4, 0)         #   value = 0

for i in range(8):
    struct.pack_into("<I", b, e1 + i * 4, 0)     # E1 = 8 个 DWORD，先全 0

f5 = e1 + 32                                     # 字段记录紧接在 E1 之后
struct.pack_into("<I", b, f5, 4)                 # tag5: len=4
struct.pack_into("<I", b, f5 + 4, 4)             #       value=4
f7 = f5 + 8
struct.pack_into("<I", b, f7, 4)                 # tag7: len=4
struct.pack_into("<I", b, f7 + 4, 4)             #       value=4
f8 = f7 + 8
struct.pack_into("<I", b, f8, 4)                 # tag8: len=4
struct.pack_into("<I", b, f8 + 4, 4)             #       value=4

struct.pack_into("<I", b, e1 + 4 * 4, f5)        # ★ E1[4] -> tag5 字段
struct.pack_into("<I", b, e1 + 6 * 4, f7)        # ★ E1[6] -> tag7 字段
struct.pack_into("<I", b, e1 + 7 * 4, f8)        # ★ E1[7] -> tag8 字段
entries[20] = nested                             # ★ key20 指向 nested
rec = f8 + 8
```

### ★★★★★ 完整内存布局（相对 `nested`）

```
nested + 0x00   u32  = e1（相对 base 的偏移）   ← ★★★ 这里是"偏移"不是"长度"！
nested + 0x04   u32  = 0
nested + 0x08   E1[0]  = 0
                E1[1]  = 0
                E1[2]  = 0
                E1[3]  = 0
                E1[4]  = f5（tag5 字段偏移）    ← ★ 第 5 个 DWORD
                E1[5]  = 0
                E1[6]  = f7（tag7 字段偏移）
                E1[7]  = f8（tag8 字段偏移）
nested + 0x28   f5: (len=4, value=4)
nested + 0x30   f7: (len=4, value=4)
nested + 0x38   f8: (len=4, value=4)
```

### ★★★ 寻址路径（第 453–463 行注释，逐字）

```
0x8250 寻址: [ebp-0x18] = [base+table[19] + (seq-1)*4]  (seq=1 -> key20 记录的 len 字段)
             [ebp-0x1c] = base + [ebp-0x18]   ← len 字段值 = 条目相对 base 的偏移!
             [ebp-0x20] = [条目 + (tag-1)*4]  ← 条目是裸 DWORD 偏移数组
             [ebp-0x24] = base + [ebp-0x20] = 字段记录 -> 读 (len,value)
0x8510(tag7) 要求字段 len 恰好 4。
```

★★★ **⇒ 四层解引用：**
```
① 用 seq 找 key19 记录 → 读出偏移
② base + 偏移 → 找到 E1 条目（8 个 DWORD 的裸数组）
③ E1[tag-1] → 字段偏移
④ base + 字段偏移 → (len, value)
```

★★★ **⇒ 关键陷阱：**key20 记录的 `len` 字段存的不是长度，是**偏移**。****

★ **⇒ 且 `E1[4]` 对应 `tag5`（`tag-1 = 4`）、`E1[6]` 对应 `tag7`、`E1[7]` 对应 `tag8`。**

★★ **⇒ `E1` 有 8 个 DWORD（`tag` 1..8），只用到了 5/7/8。**

### ★★★ `0x8510(tag7)` 要求 `len == 4`

★★ **⇒ 这与"`len != 4` 直接判失败"的约束一致。**

---

## 二、★★★★ 跳转表的**兜底填充**（第 484–488 行）

```python
b[tbl:tbl + KEY_MAX * 4] = struct.pack("<I", generic) * KEY_MAX    # ★ 全表填 generic
for k, off in entries.items():
    if 1 <= k <= KEY_MAX:
        struct.pack_into("<I", b, tbl + (k - 1) * 4, off)          # ★ 覆盖已定义项
return bytes(b)
```

★★★ **⇒ 两步：**
```
① 整个 1 MB 跳转表**先全部填成 `generic`**（一个合法的 len=4 记录）
② 再逐个覆盖**已定义**的 key
```

★★★ **⇒ 效果：任何未定义的 key 都指向 `generic` ⇒ 读到合法的 DWORD 0，而不是失败。**

★ **⇒ 这是**必需的**（因为 `len != 4` 会硬失败）。**

★ **⇒ 索引公式 `tbl + (k-1)*4` —— key 从 **1** 开始，不是 0。**

---

## 三、★★★★ `parse_patches`（第 494–509 行）

```python
# ---- 补丁机制: patch_spec.txt 里每项 "地址:十六进制字节" ----
#   "0x641654:9090"              绝对地址(仅在自己早读到原始字节时才敢用)
#   "tenproxy.dll:0x7CAF:01"     模块名:RVA  (依赖运行时算出的模块基址)
def parse_patches(spec):
    out = []
    for item in (spec or "").split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        try:
            if parts[0].lower().startswith("0x"):
                out.append((int(parts[0], 0), bytes.fromhex("".join(parts[1:])), item))
            else:
                out.append(((parts[0], int(parts[1], 0)),
                            bytes.fromhex("".join(parts[2:])), item))
        except Exception as e:
            out.append((None, None, "%s  (解析失败 %r)" % (item, e)))
    return out
```

### ★★★ 两种格式（逐字注释）

| 格式 | 例 | 含义 |
|---|---|---|
| **绝对地址** | `"0x641654:9090"` | ★ **仅在自己早读到原始字节时才敢用** |
| **模块名:RVA** | `"tenproxy.dll:0x7CAF:01"` | ★ 依赖运行时算出的模块基址 |

★★★ **⇒ 第一种格式的**警告**很重要：**
> **绝对地址（仅在自己早读到原始字节时才敢用）**

★ **⇒ 因为 ASLR/重定位会改变实际地址。**

### ★★ 返回三元组

```python
(target, data, text)
```
- `target` = `int`（绝对地址）或 `(mod, rva)` 元组
- `data` = `bytes`
- `text` = 原始字符串（用于日志）

★★ **⇒ 解析失败时 `target = None`（后续跳过）。**

---

## 四、★★★★★ `apply_patches`（第 512–545 行）—— **读-写-读 校验**

```python
def apply_patches(h, known_bases, ml, spec, log):
    """写前读 / 写后读: 任何一步不对都直接报出来(不猜)"""
    for target, data, text in parse_patches(spec):
        if target is None:
            log("-- patch 跳过 %s" % text)
            continue
        if isinstance(target, tuple):
            mod, rva = target
            mb = known_bases.get(mod.lower(), 0)
            if not mb:
                tw = time.time()
                while time.time() - tw < 40:
                    ml2 = mods_peb(h) or ml
                    mb = next((b for n, b, s in ml2
                               if n.lower().startswith(mod.lower())), 0)
                    if mb:
                        break
                    time.sleep(0.3)
            if not mb:
                log("-- patch %s 找不到模块 %s (也许还没加载)" % (text, mod))
                continue
            addr, where = mb + rva, "%s+0x%X" % (mod, rva)
        else:
            addr, where = target, "0x%08X" % target
        before = rpm(h, addr, len(data))
        if not wpm(h, addr, data):
            log("-- patch %s: %s -> 写失败" % (where, before.hex(" ")))
            continue
        after = rpm(h, addr, len(data))
        log("-- patch %s: %s -> %s (%s)" ...
```

### ★★★★★ 三个设计要点

**① 模块基址的**有界等待**（第 521–529 行）**

```python
tw = time.time()
while time.time() - tw < 40:          # ★ 最多等 40 秒
    ml2 = mods_peb(h) or ml
    mb = next((b for n, b, s in ml2 if n.lower().startswith(mod.lower())), 0)
    if mb:
        break
    time.sleep(0.3)                    # ★ 每 0.3 秒重试
```

★★★ **⇒ 最多等 **40 秒**，每 **0.3 秒**重查一次 PEB 模块链。**
**⇒ 这是为"模块还没加载"的情况设计的。**

★ **⇒ 与 docstring 的"`TenProxy.dll` 要到 t≈5s 才被加载"呼应。**

**② 读-写-读 三重校验（第 536–540 行）**

```python
before = rpm(h, addr, len(data))       # ★ 写前读
if not wpm(h, addr, data):             # 写
    log("-- patch %s: %s -> 写失败" % (where, before.hex(" ")))
    continue
after = rpm(h, addr, len(data))        # ★ 写后读
```

★★★★★ **⇒ 这是**最严谨的补丁实践**：**
```
① 写前读（记录原字节）
② 写
③ 写后读（验证）
④ 日志里打印 before → after
```

★ **⇒ 函数 docstring 明说：**写前读 / 写后读: 任何一步不对都直接报出来(不猜)**。**

**③ 模块名匹配用 `startswith`（第 526 行）**

```python
n.lower().startswith(mod.lower())
```

★★ **⇒ 因为 PEB 里的模块名是**完整文件名**（如 `tenproxy.dll`），
而 `mod` 可能只是前缀。**

★ **⇒ 用 `startswith` 允许模糊匹配。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 嵌套结构 | `key20 记录` 的 **len 字段存偏移**（不是长度） |
| 2 | 条目 E1 | **8 个 DWORD 裸数组** |
| 3 | 字段映射 | `E1[4]`→tag5 / `E1[6]`→tag7 / `E1[7]`→tag8 |
| 4 | ★ 字段记录 | `(len=4, value=4)` × 3 |
| 5 | ★★★ 四层解引用 | seq → key19 → E1 → 字段 |
| 6 | ★★ `0x8510` 约束 | **tag7 的 `len` 必须恰好 4** |
| 7 | ★★★ 跳转表填充 | **先全填 `generic`，再覆盖已定义项** |
| 8 | ★ 索引公式 | `tbl + (k-1)*4`（**key 从 1 开始**） |
| 9 | 补丁格式 1 | `"0x641654:9090"`（**绝对地址，有风险**） |
| 10 | 补丁格式 2 | `"tenproxy.dll:0x7CAF:01"`（**模块名:RVA**） |
| 11 | ★★ 绝对地址警告 | **仅在自己早读到原始字节时才敢用** |
| 12 | ★★★ 模块等待 | **最多 40 秒，每 0.3 秒重查 PEB** |
| 13 | ★★★★★ 读-写-读 | **写前读 / 写 / 写后读** |
| 14 | ★ 模块名匹配 | `startswith`（PEB 里是完整文件名） |

---

## 六、结论

### 1. ★★★★★ TCLS 镜像有**三套并存的寻址方式**

```
① 全局：key = tag
② 服务器条目：key = (seq << 16) | tag
③ 嵌套：seq → key19 → E1[tag-1] → 字段（★ 只有 tag5/7/8）
```

★★ **⇒ 第三套是最难发现的，因为它复用了 `key20` 记录的 `len` 字段存偏移。**

### 2. ★★★ 跳转表的 `generic` 兜底是**必需的**

★ **⇒ 因为 `len != 4` 会**硬失败**，必须保证任何 key 都能读到合法 DWORD。**

### 3. ★★★★★ `apply_patches` 的**读-写-读**是最严谨的补丁实践

★★ **⇒ 与"不猜"的设计哲学一致（`docstring` 原文）。**

### 4. ★★★ 模块基址的 40 秒有界等待是为 `TenProxy.dll` 的 t≈5s 加载设计的

### 5. ★★ 绝对地址格式有明确风险警告

---

## 七、下一步

- 四个兼容补丁（第 546–709 行）—— **`compat_patch_once` 的逐补丁逻辑**
- 会话密钥快照（第 710–804 行）
- `scan_dword` / `probe_auth_object` / `watch_dialogs`（第 815–949 行）
- `playerstate_probe_thread`（第 1118–1318 行）
- `main()`（第 1319 行起）
