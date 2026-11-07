# 学习报告 049（重开）— `force_display_name.py` UTF-8 截断与标签定位模式

**学习范围**：第 120–249 行（`context` / `truncate_encoded` / 参数表 / `--tag` 模式）
**性质**：全实测
**★★★ 本报告收录**UTF-8 位运算截断**与**`--tag` 标签定位的完整设计**

---

## 一、★★★ `context`（第 115–122 行）

```python
def context(handle, address, before=16, after=48):
    buf = ctypes.create_string_buffer(before + after)
    read = ctypes.c_size_t()
    if not k32.ReadProcessMemory(handle, ctypes.c_void_p(address - before), buf,
                                 before + after, ctypes.byref(read)):
        return None
    raw = buf.raw[:read.value]
    return raw
```

★★ **⇒ 读命中地址**前 16 字节 + 后 48 字节**（共 64 字节）的上下文。**

★ **⇒ 用于**人工判读**（是否真的是名字字段）。**

---

## 二、★★★★★ `truncate_encoded` —— UTF-8 位运算截断（第 125–143 行）

```python
def truncate_encoded(text, encoding, limit):
    """按编码截断到 <= limit 字节，且**不切断多字节字符**。

    名字字段是 16 字节定长（本文件 §字段）；UTF-8 下一个汉字 3 字节，
    直接 `[:16]` 会切出半个字符（悬空首字节）—— 渲染是乱码，而且与后端
    `IdentityConfig.hpp` 的 `DefaultUsername` 无法逐字节对齐（进不去服）。
    """
    data = text.encode(encoding, "replace")
    if len(data) <= limit:
        return data
    data = data[:limit]
    if encoding.replace("-", "").lower() == "utf8":
        cut = len(data)
        while cut > 0 and (data[cut - 1] & 0xC0) == 0x80:
            cut -= 1
        if cut > 0 and (data[cut - 1] & 0xC0) == 0xC0:
            cut -= 1
        data = data[:cut]
    return data
```

### ★★★★★ UTF-8 边界回退的完整算法

```
① 先按 limit 硬截断
② 若编码是 UTF-8：
     cut = len(data)
     while cut > 0 and (data[cut-1] & 0xC0) == 0x80:    ← 跳过续字节
         cut -= 1
     if cut > 0 and (data[cut-1] & 0xC0) == 0xC0:       ← 丢掉不完整首字节
         cut -= 1
     data = data[:cut]
```

### ★★★ UTF-8 编码规则（位运算的依据）

```
0xxxxxxx   单字节 ASCII
110xxxxx   2 字节字符首字节
1110xxxx   3 字节字符首字节   ← 汉字
11110xxx   4 字节字符首字节
10xxxxxx   续字节             ← (b & 0xC0) == 0x80
```

★★★ **⇒ 两步：**
```
① 从末尾往前跳过所有**续字节**（0x80..0xBF）
② 若停下的前一个字节是**首字节**（0xC0..0xFF）⇒ 丢掉它（不完整）
```

★★ **⇒ `(b & 0xC0) == 0xC0` 匹配 `110xxxxx`/`1110xxxx`/`11110xxx` 全部首字节。**

### ★★★★★ docstring 的关键警告（第 129–130 行，逐字）

```
直接 `[:16]` 会切出半个字符（悬空首字节）—— 渲染是乱码，而且与后端
`IdentityConfig.hpp` 的 `DefaultUsername` 无法逐字节对齐（进不去服）。
```

★★★ **⇒ 两个后果：**
```
① **渲染是乱码**（显示问题）
② ★★★ **与后端 `DefaultUsername` 无法逐字节对齐 ⇒ 进不去服**（★ 功能问题）
```

★ **⇒ 这与报告 033/035 的"connect 名字校验是逐位相等"**完全一致**。**

### ★★ 与 `fake_auth_tls.py` 的对比

| 文件 | 方法 | 复杂度 |
|---|---|---|
| `fake_auth_tls.py` | **按字符**回退（`name = name[:-1]` 重新编码） | O(n²) |
| **`force_display_name.py`** | **按字节**位运算 | **O(n)** |

★★ **⇒ 两种都对，后者更快。**

---

## 三、★★★★★ 七个参数（第 151–171 行）

```python
parser.add_argument("--apply", metavar="NAME", help="把名字写成这个值")
parser.add_argument("--encoding", default="gbk", choices=("gbk", "utf-8"),
                    help="写入 16 字节名字字段所用的编码（默认 gbk）")
parser.add_argument("--needle", default="AdministraClient",
                    help="要替换掉的现役名字（默认 AdministraClient）")
parser.add_argument("--list-only", action="store_true")
parser.add_argument("--wait", type=int, default=0, metavar="SECONDS", ...)
parser.add_argument("--watch", type=int, default=0, metavar="SECONDS", ...)
parser.add_argument("--tag", action="store_true", ...)
```

### ★★★ 七个参数表

| # | 参数 | 默认 | 作用 |
|---|---|---|---|
| 1 | `--apply` | None | 目标名字 |
| 2 | **`--encoding`** | **`gbk`** | ★ 写入编码 |
| 3 | **`--needle`** | **`AdministraClient`** | ★ 要替换的现役名 |
| 4 | `--list-only` | False | 只列不改 |
| 5 | `--wait` | 0 | 等客户端起来（秒） |
| 6 | `--watch` | 0 | 反复补写（秒） |
| 7 | `--tag` | False | ★ 标签定位模式 |

### ★★★ `--encoding` 的历史（第 153–154 行）

```python
# ★ 2026-10-07 15:5x -- 编码可选：默认 gbk（历史行为）；本轮起 launch_chain 传 `utf-8`
#   （依据：榜单里 GBK 的 `81 52` 被非 GBK 管线渲染成「▮R」；本客户端自身文字管线是 UTF-8）。
```

★★★ **⇒ 默认 `gbk`（历史），但 `launch_chain.py` 传 **`utf-8`**。**

★★ **⇒ 依据：**GBK 的 `81 52` 被渲染成 `▮R` ⇒ 该管线**不是** GBK 解码。**

★ **⇒ 这与报告 045 的 `fake_auth_tls.py` 的编码处理**呼应**。**

### ★★★ `--needle` 的默认值陷阱

```python
parser.add_argument("--needle", default="AdministraClient", ...)
```

★★★ **⇒ 默认 `AdministraClient` 只在 Windows 账户名是 **`Administrator`** 时成立（报告 048）。**

★ **⇒ 换账户 ⇒ 扫不到任何东西。**

★★ **⇒ 而 `launch_chain.py:388` **不传 `--needle`** ⇒ 用默认值。**

---

## 四、★★★★★ `--tag` 标签定位模式（第 164–170 行）

### 4.1 ★★★ 设计说明（第 164–168 行，逐字）

```python
# ★★ 2026-10-07 17:2x -- 标签定位模式：给每一份名字拷贝写**唯一 ASCII 标签**（Lg000…），
#   用甲方截图把「哪个界面读哪份拷贝」一次映射（右上=GBK渲染/榜单=UTF-8渲染的拷贝不同源）。
#   附带打印逐条命中表（地址+上下文）到输出，用于事后把标签号对回地址。
#   用 16 字节定长写（标签+NUL 补齐），把旧的尾部字节（GBK/UTF-8 残渣）一并清掉。
#   目标名固定用 "Lifetime" 前缀扫描（所有拷贝都有该前缀，与编码无关）。
```

### ★★★★★ 四个设计要点

| # | 要点 | 内容 |
|---|---|---|
| **1** | **目的** | 给每份拷贝写唯一标签（`Lg000`…），用**截图**建立"界面↔地址"映射 |
| **2** | **解决什么问题** | 右上 = **GBK 渲染** / 榜单 = **UTF-8 渲染**，拷贝**不同源** |
| **3** | **写入方式** | **16 字节定长**（标签 + NUL 补齐），**清掉旧尾部字节** |
| **4** | **扫描前缀** | **`b"Lifetime"`**（所有拷贝都有，**与编码无关**） |

★★★ **⇒ 第 2 条揭示了**核心矛盾**：**
```
同一份名字被多处消费
        ↓
右上角    = GBK 渲染
榜单/列表 = UTF-8 渲染
        ↓
★ 字段一份字节**不可能两边都对**
        ↓
★★★ 所以需要"给不同拷贝写不同编码" ⇒ 先要**知道哪个界面读哪份拷贝**
        ↓
⇒ `--tag` 模式：写唯一标签，看界面显示哪个
```

★ **⇒ 这与报告 019 的 `launch_chain.py` 注释**完全一致**。**

### 4.2 ★★★ `TAG_NEEDLE = b"Lifetime"`（第 175 行）

```python
TAG_NEEDLE = b"Lifetime"
```

★★★ **⇒ 用 `Lifetime` 而不是 `AdministraClient` —— 因为：**
```
"Lifetime" 是 8 个 ASCII 字符
        ↓
GBK 和 UTF-8 编码**逐字节相同**
        ↓
★ 所以不论哪份拷贝都能被扫到
```

★★ **⇒ 注释（第 168 行）：**"所有拷贝都有该前缀，与编码无关"。**

★ **⇒ 而 `AdministraClient` 也是 ASCII，但只有**特定账户**才有。**

### 4.3 ★★★ 写入逻辑（第 217–238 行）

```python
written_now = 0
for index, address in enumerate(hits_now):
    payload = ("Lg%03d" % index).encode("ascii")        # ★ Lg000, Lg001, ...
    payload = payload + b"\x00" * (16 - len(payload))   # ★ 16 字节定长
    old = wintypes.DWORD()
    if not k32.VirtualProtectEx(handle_now, ctypes.c_void_p(address),
                                len(payload), PAGE_EXECUTE_READWRITE,
                                ctypes.byref(old)):
        continue
    done = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(handle_now, ctypes.c_void_p(address),
                                payload, len(payload), ctypes.byref(done))
    k32.VirtualProtectEx(handle_now, ctypes.c_void_p(address),
                         len(payload), old, ctypes.byref(wintypes.DWORD()))
    if ok and done.value == len(payload):
        written_now += 1
```

### ★★★ 三步写内存（与 `nt10.py` 的 `_wpm_code` 相同，但**少了 `FlushInstructionCache`**）

```
① VirtualProtectEx → PAGE_EXECUTE_READWRITE
② WriteProcessMemory
③ ★ VirtualProtectEx → 恢复原保护
```

★★ **⇒ **没有 `FlushInstructionCache`** —— 因为改的是**数据**（名字字符串），不是代码。**

★ **⇒ 这是**正确的**（数据不需要刷指令缓存）。**

### ★★ 标签格式

```python
payload = ("Lg%03d" % index).encode("ascii")     # Lg000, Lg001, ..., Lg999
```

★★ **⇒ `Lg` + 3 位数字（`Lg000`..`Lg999`），最多 **1000** 个。**

### 4.4 ★★★ 命中表打印（第 239–246 行）

```python
for index, address in enumerate(hits_now):
    raw = context(handle_now, address)
    if raw:
        head = " ".join("%02X" % c for c in raw[8:16])
        text = "".join(chr(c) if 32 <= c < 127 else "." for c in raw)
        print("    pid=%d Lg%03d  0x%08X  头[%s]  %s"
              % (pid_now, index, address, head, text))
```

★★★ **⇒ 打印三样：标签号、地址、**上下文（含 `raw[8:16]` 的 hex 和 ASCII 侧栏）**。**

★ **⇒ `raw[8:16]` —— 因为 `context` 读了前 16 字节，`[8:16]` 是**名字字段本身的头 8 字节**。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `context` | 前 **16** + 后 **48** = **64** 字节 |
| 2 | ★★★★★ **UTF-8 截断** | 位运算：跳续字节 `(b&0xC0)==0x80`，丢首字节 `(b&0xC0)==0xC0` |
| 3 | ★★★ **截断错误后果** | **乱码 + 进不去服**（无法与 `DefaultUsername` 逐字节对齐） |
| 4 | ★ 复杂度 | 本文件 **O(n)** / `fake_auth_tls` O(n²) |
| 5 | ★★★ 七参数 | `--apply` / `--encoding` / `--needle` / `--list-only` / `--wait` / `--watch` / `--tag` |
| 6 | ★ `--encoding` 默认 | **`gbk`**（历史），`launch_chain` 传 **`utf-8`** |
| 7 | ★★ `--needle` 默认 | **`AdministraClient`**（只在 `Administrator` 账户成立） |
| 8 | ★★★★★ **`--tag` 目的** | 写唯一标签 ⇒ 用**截图**建立"界面↔地址"映射 |
| 9 | ★★★ **核心矛盾** | 右上=**GBK** / 榜单=**UTF-8**，一份字节不可能两边都对 |
| 10 | ★★★ 扫描前缀 | **`b"Lifetime"`**（ASCII，**与编码无关**） |
| 11 | 标签格式 | **`Lg%03d`**（`Lg000`..`Lg999`），**16 字节定长**（NUL 补齐） |
| 12 | ★★ 写内存三步 | `VirtualProtectEx` → `WriteProcessMemory` → **恢复** |
| 13 | ★ 无 `FlushInstructionCache` | 因为改的是**数据**不是代码 |
| 14 | 命中表 | 标签号 + 地址 + **`raw[8:16]` 头 8 字节** + ASCII 侧栏 |

---

## 六、结论

### 1. ★★★★★ **UTF-8 截断的位运算实现**比字符回退快（O(n) vs O(n²)）

★ **⇒ 两种都对，本文件的更快。**

### 2. ★★★★★ **截断错误会导致"进不去服"**（不只是乱码）

★ **⇒ 因为 `connect` 校验是逐字节相等。**

### 3. ★★★★★ **`--tag` 模式是"用实验建立映射"的典范**

```
写 Lg000..LgNNN 到每份拷贝
        ↓
看界面显示哪个
        ↓
★ 建立"界面↔地址"映射
        ↓
再按拷贝分编码写入
```

### 4. ★★★ **"Lifetime" 前缀与编码无关**（ASCII ⇒ GBK/UTF-8 字节相同）

### 5. ★★ **`--needle` 默认 `AdministraClient` 只在 `Administrator` 账户成立**

### 6. ★★ 改数据不需要 `FlushInstructionCache`（与改代码不同）

---

## 七、下一步

- `force_display_name.py` 剩余（第 249 行起）—— `--watch` / `--wait` / 主流程
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
