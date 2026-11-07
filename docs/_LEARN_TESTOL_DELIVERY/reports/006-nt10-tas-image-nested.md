# 学习报告 006 — TCLS 共享内存镜像的嵌套结构（nt10.py 行 367-489）

**学习范围**：`build_tas_image` 全部 —— TCLS_SHAREDMEMEMORY 的二进制布局
**这是整个包里最难的逆向成果**

---

## 一、整体布局（行 386-399）

```python
KEY_MAX = 0x40000                      # 262,144 个 key 槽
IMG_LEN = 4 + KEY_MAX * 4 + 0x8000    # = 4 + 1,048,576 + 32,768 ≈ 1.08 MB
b = bytearray(IMG_LEN)
struct.pack_into("<I", b, 0, 0x40)     # 魔数
tbl, rec = 4, 4 + KEY_MAX * 4          # 表在 +4，记录区在 +0x100004
```

```
偏移            大小              内容
0x0             4                 魔数 0x40
0x4             0x100000 (1MB)    跳转表：KEY_MAX 个 DWORD，key-1 索引
0x100004        0x8000 (32KB)     记录区：(u32 len)(value)，16 字节对齐
```

### `put()` 的分配逻辑（行 393-399）

```python
def put(key, val):
    entries[key] = rec                          # 记录当前偏移
    struct.pack_into("<I", b, rec, len(val))    # 写长度
    b[rec+4 : rec+4+len(val)] = val             # 写值
    rec += 4 + len(val)
    rec = (rec + 15) & ~15                      # ★ 16 字节对齐
```

★ **记录格式是 `(u32 len)(value)`**，和魔数后紧跟的表结构一致。
★ **16 字节对齐**：`(rec + 15) & ~15` 向上取整。为什么？可能是 TenProxy 用了 SSE 或要求对齐访问。

---

## 二、两套命名空间

### ① 全局命名空间：`key = tag`（行 417-448）

| tag | 内容 | 长度 | 说明 |
|---|---|---|---|
| 1 | `d4(0)` | 4 | DWORD |
| 2 | `d4(0)` | 4 | DWORD |
| 3 | 0x00×1 | 1 | 单字节 |
| 4 | `"0123456789ABCDEF"*8` | 128 | **LoginKey** |
| 5 | 0x00×0x10 | 16 | |
| 6 | `d4(0)` | 4 | DWORD |
| 7 | 0x00×0x200 | 512 | |
| 8 | 0x00×0x200 | 512 | |
| 14 | 0x00×0x410 | 1040 | |
| 15 | 0x00×0x410 | 1040 | ★ 上一版**漏了这个** |
| 16 | 0x00×0x28 | 40 | |
| 17 | `d4(1)` | 4 | |
| **18** | **`d4(1)`** | 4 | ★ **必须是条目序号 1** |
| 19 | 0x00×0x208 | 520 | |
| 22 | `"0123456789ABCDEF"` | 16 | 票据 |
| 24 | `"0123456789ABCDEF"*8` | 128 | 大 blob |
| **25** | **`"10001\0"+0x00×10`** | 16 | **OpenID** |
| 26 | 0x00×1 | 1 | |
| 27 | `0xA5×0x70` | 112 | 非零 blob |

### 关键注释（行 442-444）

> `exe 0x641600` 段收集登录信息时读这几个 tag 并格式化：
> **tag25 = OpenID**，格式串 `0xdc7104` = `"OpenID LoginKey: %s"`
> → **全 0 = 空账号 = 认证失败**

★ **这是"内容必须非零"的原因**：空 OpenID → 认证失败。

### ② 服务器条目命名空间：`key = (seq<<16) | tag`（行 405-415）

```python
entry = (1 << 16)                       # seq = 1
put(entry|2, name.encode("gbk")+b"\x00")   # 服务器名
put(entry|4, host.encode("gbk")+b"\x00")   # ★ host
put(entry|3, d4(port))                     # ★ 端口
put(entry|5, d4(1))
put(entry|6, d4(0))
put(entry|7, d4(0))
put(entry|8, d4(0))                        # 新增
```

★ **`(seq<<16)|tag`**：高位是服务器序号，低位是 tag。
`seq=1` 所以 key 是 `0x10002`、`0x10004`、`0x10003`……

---

## 三、历史 bug 记录（行 383-384）

> 上一版两个根因：
> **(a) 漏了 tag 15**
> **(b) 用 "key+小步长" 铺服务器条目，结果 `0x18+3=27` 把全局 tag 27 覆盖成了端口 DWORD**
> —— DWORD 路径会因 `len!=4` 直接判失败（不是"内容为空"）

### bug (b) 的机制

```
如果服务器条目用 "entry + 0,1,2,3..." 铺：
  entry = 0x10000
  0x10000 + 3 = 0x10003  ← 这是对的
但若从 0x18 开始：0x18+3 = 0x1B ...
```

实际描述的是：**用递增 key 而不是 `(seq<<16)|tag`**，导致 key 碰撞到全局 tag。

★ **`len != 4` 会"直接判失败"而不是"内容为空"** —— 这个区别很重要：
DWORD 读取路径看到 `len != 4` 时**不会尝试读 4 字节**，而是**整个失败**。

---

## 四、嵌套结构（行 453-483）—— 最精妙的部分

### 注释原文（行 453-459）

> vtable[12] (`0x8250`) / vtable[14] (`0x8510`) 读 tag7/tag8 用的是**嵌套结构**，
> **不是** `(seq<<16)|tag`！
>
> `0x8250` 寻址：
> ```
> [ebp-0x18] = [base + table[19] + (seq-1)*4]   (seq=1 → key20 记录的 len 字段)
> [ebp-0x1c] = base + [ebp-0x18]                ← len 字段值 = 条目相对 base 的偏移!
> [ebp-0x20] = [条目 + (tag-1)*4]               ← 条目是裸 DWORD 偏移数组
> [ebp-0x24] = base + [ebp-0x20]                = 字段记录 → 读 (len,value)
> ```
> `0x8510`(tag7) 要求字段 `len` 恰好 4。

### 布局图解

```
key20 记录 (在记录区)
  +0: len  = E1_offset        ← ★ 这里存的是"偏移"，不是长度！
  +4: value = 0

E1 条目 (8 个 DWORD 裸数组)
  +0x00: 0
  +0x04: 0
  ...
  +0x10: f5_offset   ← E1[4] → tag5 字段
  +0x18: f7_offset   ← E1[6] → tag7 字段
  +0x1C: f8_offset   ← E1[7] → tag8 字段

字段记录 (每个 8 字节)
  f5: (len=4, value=4)      ← tag5
  f7: (len=4, value=4)      ← tag7
  f8: (len=4, value=4)      ← tag8
```

### 代码实现（行 464-483）

```python
nested = rec
e1 = nested + 8                                  # 条目在 key20 记录之后 8 字节
struct.pack_into("<I", b, nested, e1)            # ★ key20 的 len 字段 = E1 偏移
struct.pack_into("<I", b, nested + 4, 0)         # value = 0

for i in range(8):
    struct.pack_into("<I", b, e1 + i*4, 0)       # E1 = 8 个 DWORD，先全 0

f5 = e1 + 32                                     # 字段记录紧接在 E1 之后
struct.pack_into("<I", b, f5, 4)                 # len = 4
struct.pack_into("<I", b, f5+4, 4)               # value = 4
f7 = f5 + 8
... (同样)
f8 = f7 + 8

struct.pack_into("<I", b, e1 + 4*4, f5)          # E1[4] = f5 偏移
struct.pack_into("<I", b, e1 + 6*4, f7)          # E1[6] = f7 偏移
struct.pack_into("<I", b, e1 + 7*4, f8)          # E1[7] = f8 偏移

entries[20] = nested                             # key20 指向 key20 记录
rec = f8 + 8
```

### 为什么 tag5/tag7/tag8 要放进这个嵌套结构

因为 `0x8250`/`0x8510` 是 **4 参带序号** 的取值函数：`(tag, dst, &len, seq)`。
它**不查 `(seq<<16)|tag`**，而是：
1. 用 `seq` 找到 key19 记录，读出偏移
2. 用偏移找到 E1 条目
3. 用 `tag` 索引 E1，得到字段偏移
4. 读字段记录 `(len, value)`

★ **两套寻址共存**：大部分 tag 走 `(seq<<16)|tag`，但 tag5/7/8 走嵌套。

---

## 五、兜底记录（行 449-452）

```python
generic = rec
struct.pack_into("<I", b, rec, 4)    # len = 4
rec += 16
```

★ **为什么需要兜底**：
```python
b[tbl:tbl+KEY_MAX*4] = struct.pack("<I", generic) * KEY_MAX
```

**整个表先全部填成 `generic` 偏移**（一个合法的 `len=4` 空记录）。
这样**任何未定义的 key 都能读到一个合法 DWORD**，而不是越界或长度不符。

★★ **这是一个非常聪明的设计**：与其让未定义 key 报错，不如**全部返回 0 DWORD**。
因为 DWORD 路径 `len != 4` 会"直接判失败"（见 bug (b)），
所以必须保证**每个 key 都指向一个 len==4 的记录**。

---

## 六、`rec = (rec + 15) & ~15` 对齐的影响

**为什么 16 字节对齐**：
- `E1` 是 8 个 DWORD 裸数组，需要 4 字节对齐
- 字段记录是 `(len, value)`，也是 4 字节对齐
- 16 字节可能是为了 **SSE 拷贝**（`movaps` 要求 16 字节对齐）

★ 但代码里 `put()` 用 16 对齐，而嵌套结构手工计算偏移（`e1 = nested + 8`）——
**手动布局不遵守 16 对齐**。这没问题，因为嵌套结构内部只要求 4 字节对齐。

---

## 七、这一块的结论

1. **镜像 = 魔数 + 1MB 跳转表 + 记录区**，记录是 `(len,value)` 16 字节对齐。
2. **两套命名空间**：全局 `key=tag`，服务器 `key=(seq<<16)|tag`。
3. **tag5/7/8 走第三套嵌套寻址**，不是 `(seq<<16)|tag`。
4. **`tag18` 必须是条目序号 1**（不是 0x200，那是旧的错误值）。
5. **整个表兜底填 `generic`**，保证任何 key 都返回合法 DWORD。
6. **内容不能全 0**：`tag25`(OpenID) 全 0 → 认证失败。

---

## 八、待验证

- [ ] `0x8250`/`0x8510` 的完整反汇编（确认 4 层解引用）
- [ ] 为什么 `E1` 是 **8** 个 DWORD（tag 最大到 8？）
- [ ] `tag 20` 的 `key20 记录` 里 `len` 字段存偏移是不是特例（正常应是长度）
- [ ] `0x40000` (262144) 这个 KEY_MAX 从哪来
- [ ] 16 字节对齐是否真的被 TenProxy 要求
