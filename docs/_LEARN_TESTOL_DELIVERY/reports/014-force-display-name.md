# 学习报告 014 — force_display_name.py 逐行（19,288 B / 389 行）

**学习范围**：`bundle\force_display_name.py` 全文
**核心发现**：这是"四条服务端通道全部被否证 → 只能改内存"的完整判决书

---

## 一、它解决什么（行 1-16）

> 界面显示的是 `AdministraClient`，而且：
> * **服务端能给的三个通道全被客户端忽略** —— 认证应答 ticket `+33`、
>   认证应答 `extra_data.username`(base64)、`Identity.json` 的 `displayName`
> * **TCLS 共享内存里的名字客户端一个字节都不读**（注入 `name=CODOL-LOCAL`，
>   在 **1,517 MB** 内存里命中 **0** 次）
> * **`Platformwrapper` 的 Tencent 接口（`Tencent.cpp:35-53`）没有任何名字槽位**
> * **磁盘上搜不到 `AdministraClient` 这个串** ⇒ 它是运行期用 Windows 账户名
>   `Administrator` 拼出来的（`Administra` + `Client` = **16 字节，正好是字段容量**）

★★★ **这是全包最硬的定因记录：四条路全部实测排除，只剩内存。**

---

## 二、★★★ `AdministraClient` 是怎么来的（行 12-13）

```
Windows 账户名：Administrator
        ↓ 取前 10 字节
"Administra"
        ↓ + "Client"
"AdministraClient" = 16 字节  ← 正好是字段容量
```

★★ **`16 = 10 + 6`** —— **不是巧合，是"截断到字段大小"的算法**：
```c
strncpy(dst, username, 10);      // 或 snprintf(dst, 16, "%sClient", user[:10])
strcat(dst, "Client");
```

★ **如果账户名是 `Z7-CT5N1`**（本机），名字会是：
```
"Z7-CT5N1" + "Client" = "Z7-CT5N1Client" = 13 字节
```
**不一定填满 16** —— 取决于具体算法。

★★ **这意味着**：**换个 Windows 账户名，界面名字就变了**。
这是一个**没被利用的杠杆** —— 但改账户名要重启，不如改内存。

★ **也意味着**：搜索 `AdministraClient` 只对 `Administrator` 账户有效。
**换账户后必须改 `--needle` 参数。**

---

## 三、内存扫描的核心（行 80-112）

### `regions()` —— 枚举可读区（行 80-92）

```python
address = 0
while address < 0x7FFFFFFF:                  # ★ 32 位地址空间上限
    if not VirtualQueryEx(handle, address, &mbi, sizeof(mbi)):
        break
    size = mbi.RegionSize
    if size == 0: break
    if mbi.State == MEM_COMMIT and mbi.Protect in READABLE:
        yield address, size
    address += size
```

```python
READABLE = (0x02, 0x04, 0x20, 0x40)
#            PAGE_READONLY, PAGE_READWRITE, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE
```

★★ **`0x7FFFFFFF` 而不是 `0xFFFFFFFF`** —— 32 位用户态上限。
★ **注意 `PAGE_GUARD (0x100)` 和 `PAGE_NOACCESS (0x01)` 被正确排除。**

### `scan()` —— 全区搜索（行 95-112）

```python
for base, size in regions(handle):
    buf = ctypes.create_string_buffer(size)          # ★ 按区大小分配
    if ReadProcessMemory(handle, base, buf, size, &read) and read.value:
        data = buf.raw[:read.value]
        total += len(data)
        start = 0
        while True:
            index = data.find(needle, start)
            if index < 0: break
            hits.append(base + index)
            start = index + 1                        # ★ +1 而不是 +len(needle)
```

★ **`start = index + 1`** —— 允许**重叠匹配**。对固定串无所谓，但对通用字符串更安全。

★★ **`total` 累加的是实际读到的字节数** —— 所以能报"扫描 1517 MB"。
**这比"扫了多少个区"有意义。**

### ★ 一个潜在问题（不是 bug，是限制）

```python
buf = ctypes.create_string_buffer(size)
```

**如果某个区 `size` 很大（如 1 GB 的映射区），这会一次性分配 1 GB。**
在 32 位 Python 上可能失败。

★ 但实测报了 `1,517 MB` 总量，说明**分区大小可接受**（逐个区读，不是全读）。

---

## 四、UTF-8 截断的不切断字符（行 125-143）★ 最精确的一段

```python
def truncate_encoded(text, encoding, limit):
    data = text.encode(encoding, "replace")
    if len(data) <= limit:
        return data
    data = data[:limit]
    if encoding.replace("-", "").lower() == "utf8":
        cut = len(data)
        while cut > 0 and (data[cut - 1] & 0xC0) == 0x80:   # 跳过续字节 10xxxxxx
            cut -= 1
        if cut > 0 and (data[cut - 1] & 0xC0) == 0xC0:      # 丢掉不完整的首字节 110xxxxx
            cut -= 1
        data = data[:cut]
    return data
```

### ★★ 这是正确的 UTF-8 边界回退

```
UTF-8 编码规则（首字节）：
  0xxxxxxx   单字节 ASCII
  110xxxxx   2 字节字符首字节
  1110xxxx   3 字节字符首字节   ← 汉字
  11110xxx   4 字节字符首字节   ← emoji
  10xxxxxx   续字节             ← (b & 0xC0) == 0x80
```

**算法**：
1. 从末尾往前，跳过所有续字节（`0x80..0xBF`）
2. 如果停下的前一个字节是**首字节**（`0xC0..0xFF`）→ 丢掉它（不完整）

★★ **注意 `(data[cut-1] & 0xC0) == 0xC0` 匹配的是 `110xxxxx`/`1110xxxx`/`11110xxx`
全部首字节** —— 这个判断是够的，因为续字节已在第一步跳完。

★ **但有一个边界情形**：如果截断点正好在一个 4 字节字符中间，会丢掉整个字符。
**这是正确行为**（宁可少一个字符，不要半个）。

### 与 `fake_auth_tls.py` 的对比（报告 011 第四节）

| 文件 | 方法 | 评价 |
|---|---|---|
| `fake_auth_tls.py` | **按字符**回退（`name = name[:-1]` 重新编码） | 正确但 O(n²) |
| `force_display_name.py` | **按字节**位运算判断 | 正确且 O(n) |

★ **两种都对**，后者更快。**`fake_auth_tls.py` 的写法更直观**（无需懂 UTF-8 编码规则）。

### ★★ 注释里的关键警告（行 128-130）

> 直接 `[:16]` 会切出半个字符（悬空首字节）—— **渲染是乱码**，
> 而且与后端 `IdentityConfig.hpp` 的 `DefaultUsername` **无法逐字节对齐（进不去服）**。

★★ **"进不去服"** —— 这不是显示问题，是**认证失败**。
**名字字段的字节必须与后端档案一致**，否则认证比对不上。

★ 这解释了为什么名字改错会导致**进不去服**而不只是显示错。

---

## 五、★★ `--watch` 的必要性（行 253-256）

> 客户端从启动到进大厅会**多次重建**名字结构
> （实测：**132 MB 时 5 处，完全起来后 10 处**），**写一次不够**。
> 这里在给定时限内反复扫描+补写，命中就写，没有就等 2 秒再看；到点退出。
> **不是猜时间——每次都是"扫到才写"。**

### 实测数据

| 阶段 | 内存 | 命中数 |
|---|---|---|
| 启动中 | 132 MB | **5 处** |
| 完全起来 | 1,517 MB | **10 处** |

★★ **两个关键数字**：
1. **命中数 5 → 10** —— 名字结构被**重建/新增**
2. **内存 132 MB → 1,517 MB** —— 客户端起来了

★★★ **这解释了为什么"改一次"会失效**：
**客户端在大厅加载后会重新分配名字结构，旧的地址作废。**

### 实现（行 257-299）

```python
deadline = time.time() + args.watch
while time.time() < deadline:
    pid_now = find_pid()
    hits_now, _ = scan(handle_now, args.needle.encode("ascii"))
    if hits_now:
        payload_now = truncate_encoded(args.apply, args.encoding, len(args.needle))
        for address in hits_now:
            VirtualProtectEx(..., PAGE_EXECUTE_READWRITE, ...)
            WriteProcessMemory(...)
            VirtualProtectEx(..., old, ...)          # ★ 恢复原保护
    time.sleep(2)
```

★ **每 2 秒一轮，扫到才写，写后恢复页保护。**

★★ **注意它只扫 `args.needle`（旧名字）** —— 写过的位置变成新名字，
下一轮扫不到，**只补写新增的**。这是**幂等**设计。

---

## 六、★ `--tag` 标签定位模式（行 164-251）★★ 方法论价值最高

### 目的（行 164-167）

> 给每一份名字拷贝写**唯一 ASCII 标签**（`Lg000…`），用甲方截图把
> 「**哪个界面读哪份拷贝**」一次映射
> （**右上=GBK 渲染 / 榜单=UTF-8 渲染的拷贝不同源**）。
> 附带打印逐条命中表（地址+上下文）到输出，用于事后把标签号对回地址。
> 用 16 字节定长写（标签+NUL 补齐），把旧的尾部字节（GBK/UTF-8 残渣）一并清掉。

### 实现（行 173-251）

```python
TAG_NEEDLE = b"Lifetime"                        # ★ 所有拷贝都有该前缀，与编码无关
...
for index, address in enumerate(hits_now):
    payload = ("Lg%03d" % index).encode("ascii")   # Lg000, Lg001, ...
    payload = payload + b"\x00" * (16 - len(payload))   # 16 字节定长
    VirtualProtectEx / WriteProcessMemory / VirtualProtectEx
```

### ★★★ 这是一个**极其聪明的实验设计**

```
给 10 份名字拷贝各写一个唯一标签：
    Lg000, Lg001, ..., Lg009
        ↓
看界面：
    右上角显示 "Lg003"  ⇒ 右上读第 4 份
    榜单显示 "Lg007"    ⇒ 榜单读第 8 份
        ↓
有了"读哪份"的映射，就能：
    * 只改界面可见的那份（省事）
    * 或者按不同位置写不同名字（右上中文、榜单 ASCII）
```

★★ **这解决了"多份拷贝，不知道哪个生效"的根本问题。**
**不靠猜，靠一次实验把映射表建出来。**

### ★ `TAG_NEEDLE = b"Lifetime"` 的选择

> 目标名固定用 **"Lifetime"** 前缀扫描（**所有拷贝都有该前缀，与编码无关**）。

★ **"与编码无关"是关键**：`Lifetime` 是 8 个 ASCII 字符，
GBK 和 UTF-8 编码都是逐字节相同 —— **所以不论哪份拷贝都能被扫到**。

**而 `AdministraClient` 也是 ASCII，同理。**
但 `--tag` 用 `Lifetime` 说明**甲方当时的实际名字前缀是 `Lifetime`**。

---

## 七、`--needle` 的默认值是个陷阱（行 157-158）

```python
parser.add_argument("--needle", default="AdministraClient",
                    help="要替换掉的现役名字（默认 AdministraClient）")
```

★★ **`AdministraClient` 只在 Windows 账户名是 `Administrator` 时成立。**
**交付包直接跑，如果账户不是 `Administrator`，扫不到任何东西。**

★ 而 `--tag` 模式的 `Lifetime` 是**硬编码的**（行 175），说明甲方实际用的名字是
`Lifetime...`（可能就是 `Lifetime丷`，见报告 010 第五节）。

★★ **所以交付包的默认值 `AdministraClient` 与甲方实际环境（`Lifetime丷`）不一致**——
这是**又一处"开发环境 ≠ 交付环境"**。

---

## 八、内存写保护的三个调用（行 363-378）

```python
old = wintypes.DWORD()
VirtualProtectEx(handle, addr, len(payload), PAGE_EXECUTE_READWRITE, &old)  # 1
WriteProcessMemory(handle, addr, payload, len(payload), &done)             # 2
VirtualProtectEx(handle, addr, len(payload), old, &dummy)                  # 3  ★ 恢复
```

★★ **三步缺一不可**：
1. 改成可写
2. 写
3. **恢复原保护** ← 少了这一步，可能让只读段变成可执行+可写，触发异常

★ **`PAGE_EXECUTE_READWRITE` 而不是 `PAGE_READWRITE`** ——
因为名字结构可能在 `.text`/`.rdata` 里（只读段），改成 `READWRITE` 会失败。
**用 `EXECUTE_READWRITE` 最宽松。**

### ★★ 这是 `nt10.py` 里"兼容补丁"的同一套技术

报告 002/003 讲的四个兼容补丁，用的就是 `VirtualProtectEx + WriteProcessMemory`。
**`force_display_name.py` 是同一个模式的独立应用。**

---

## 九、回读验证（行 380-382）

```python
again, _ = scan(handle, needle)          # 旧名字还剩几处
after, _ = scan(handle, replacement)     # 新名字有几处
print("回读：旧名字剩 %d 处，新名字 %d 处" % (len(again), len(after)))
```

★★ **这是正确的自我验证**：
- 旧名字剩 **0** 处 ⇒ 全部改完
- 新名字有 **N** 处 ⇒ 与命中数一致

★ **但要注意**：新名字如果是 `Lg000` 这类，`replacement` 是完整 16 字节 payload，
而 `scan` 扫的是 `replacement`（不含 NUL 补齐）。**短名字会扫到多余的**。

**例如**：`replacement = b"FF0"`，扫 `b"FF0"` 会命中所有含 `FF0` 的地方。
**这不是 bug，是"回读"的近似检查**。

---

## 十、`find_pid()` 的实现（行 60-77）

```python
snap = CreateToolhelp32Snapshot(0x00000002, 0)      # TH32CS_SNAPPROCESS
...
if entry.szExeFile.decode("latin1").lower() == TARGET.lower():
    return entry.th32ProcessID
```

★ **`0x00000002` = `TH32CS_SNAPPROCESS`**。

★★ **注意这与 `nt10.py` 的冲突**：
记忆里说 **TP3/ACE 防作弊阻止 toolhelp 模块枚举**。
但**进程枚举（`SNAPPROCESS`）通常还能用**（模块枚举 `SNAPMODULE` 被拦）。

★ **所以 `force_display_name.py` 能工作，`nt10.py` 的模块枚举不行** —— 这是不同的 API。

★★ **`.decode("latin1")`** —— 正确（`szExeFile` 是 ANSI 字节，latin1 不会抛异常）。

---

## 十一、这一块的结论

### 定因判决（★★★ 最有价值）

**四条服务端通道全部被客户端忽略**：

| 通道 | 状态 | 证据 |
|---|---|---|
| ticket `+33` | ✗ 忽略 | 定因文档 |
| `extra_data.username` (b64) | ✗ 忽略 | 同上 |
| `Identity.json` `displayName` | ✗ 忽略 | 同上 |
| TCLS 共享内存 | ✗ 忽略 | 注入 `CODOL-LOCAL`，1517 MB 命中 **0** |
| Platformwrapper Tencent 接口 | ✗ **无槽位** | `Tencent.cpp:35-53` |

⇒ **名字是客户端自己造的**：`Administrator[:10] + "Client" = "AdministraClient"`（16 字节）

★★★ **这是一个"从源码/协议层完全无解，只能改内存"的案例。**

### 学到的技术

1. **内存扫描三步**：`VirtualQueryEx` 枚举 → `ReadProcessMemory` 读 → `find` 定位
2. **内存写三步**：`VirtualProtectEx(EXECUTE_READWRITE)` → `WriteProcessMemory` → **恢复原保护**
3. **名字结构会重建**：132 MB 时 5 处 → 1517 MB 时 10 处 ⇒ **必须 `--watch` 反复补写**
4. **UTF-8 定长截断**：位运算 `(b & 0xC0) == 0x80` 跳续字节，比字符串回退快
5. **`--tag` 标签法**：给每份拷贝唯一 ASCII 标签，用截图建立"界面↔地址"映射
6. **名字字节必须与后端一致**，否则**进不去服**（不只是显示错）

### ★ 交付包的两个环境错配

| 参数 | 交付包默认 | 甲方实际 |
|---|---|---|
| `--needle` | `AdministraClient` | `Lifetime...` |
| `--encoding` | `gbk`（历史） | `utf-8`（launch_chain 传） |

★ **`--tag` 里硬编码 `Lifetime` 暴露了真实环境**，而 `--needle` 默认值还是旧的。

---

## 十二、待验证（关键）

- [ ] ★★ **`Administrator[:10] + "Client"` 的算法是否准确**（换本机账户 `Z7-CT5N1` 验证）
- [ ] `--tag` 的实测结果（哪份拷贝对应右上/榜单）—— 是否有记录文件
- [ ] 名字结构在内存里的**完整布局**（16 字节之外还有什么字段）
- [ ] 为什么 `Lifetime丷` 在榜单是 `▮R`（GBK 被按 UTF-8 解）但右上正常 → **两份拷贝不同源**
- [ ] 1,517 MB 内存全扫的**耗时**（实测数据）
- [ ] 是否有"改一次就够"的场景（不进大厅时）
