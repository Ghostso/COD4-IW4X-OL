# `CCoderRWFilter` · 编解码器逐指令逆向

> 对象：`IIPSVFS.dll` 中的 `CCoderRWFilter`（导出名 `ICreateCoderRWFilter`）
> 这是 `.ifs` VFS 的编解码过滤器
> 证据：`tools/disasm.py` 逐指令反汇编，全表可复跑

---

## 1. 对象布局

工厂 `ICreateCoderRWFilter`（@ `0x10003330`）：

```asm
0x10003330  push ebp / mov ebp,esp
0x10003336  mov eax, [ebp+8]          ; 参数
0x10003339  mov [0x100315b0], eax     ; 保存为全局 logger
0x1000333e  push 8
0x10003340  call 0x10021030           ; operator new(8)
0x1000334b  cmp [ebp-0xc], 0          ; 分配失败？
0x10003351  mov ecx, [ebp-0xc]
0x10003354  call 0x10002eb0           ; 构造
```

**对象只有 8 字节**：`operator new(8)`。

### 构造函数 @ `0x10002eb0`

```asm
mov eax, [ebp-4]
mov dword ptr [eax],   0x10029454   ; vtable（基类部分）
mov dword ptr [ecx],   0x1002943c   ; vtable（CCoderRWFilter）
mov dword ptr [edx+4], 0            ; 字段 [obj+4] = 0  ← 编解码表指针
```

| 偏移 | 内容 |
|---|---|
| +0 | vptr = `0x1002943C` |
| +4 | **编解码表指针**（初值 0） |

---

## 2. vtable 六项

| 序号 | 地址 | 作用（由代码行为推断） |
|---|---|---|
| [0] | `0x10002f00` | 析构 / 分配包装 |
| [1] | `0x10002f50` | `GetSize` |
| [2] | `0x10002fc0` | **编码（Encode）** |
| [3] | `0x10003130` | **解码（Decode）** |
| [4] | `0x100032e0` | **选表（SelectMethod）** |
| [5] | `0x100030f0` | **半字节查表** |

---

## 3. ★ 核心算法：半字节查表（@ `0x10002fc0` → `0x100030f0`）

### 编码循环（`0x10003050` 起）

```asm
; 遍历输入 buffer（[ebp-0x18]，长度 [ebp-0xc]）
loop:
0x1000307a  movzx eax, byte ptr [edx]     ; b = in[i]
0x1000307d  and   eax, 0xF0
0x10003082  sar   eax, 4                  ; hi = b >> 4
0x10003085  mov   [ebp-0x1d], al          ; 保存 hi

0x1000308e  movzx edx, byte ptr [ecx]
0x10003091  and   edx, 0x0F               ; lo = b & 0x0F
0x10003094  mov   [ebp-0x1e], dl

0x10003097  push  hi
0x1000309e  call  0x100030f0              ; lookup(hi)
0x100030a9  mov   byte ptr [edx + ecx*2], al     ; out[2i] = lookup(hi)

0x100030ac  push  lo
0x100030b3  call  0x100030f0              ; lookup(lo)
0x100030be  mov   byte ptr [edx + ecx*2 + 1], al ; out[2i+1] = lookup(lo)
```

**一个输入字节 → 两个输出字节。**

### 查表函数（@ `0x100030f0`）

```asm
0x100030f9  mov byte ptr [ebp-5], 0x20    ; 默认值 = ' ' (空格)
0x10003100  mov ecx, dword ptr [eax+4]    ; 表指针 = [obj+4]
0x10003106  movzx edx, byte ptr [ebp+8]   ; 索引
0x1000310a  cmp edx, 0x10                 ; 越界检查（>= 16）
0x1000310d  jge 0x1000311c                ; 越界 → 返回 0x20
0x10003116  mov dl, byte ptr [ecx + eax]  ; 表[index]
0x10003119  mov [ebp-5], dl
0x1000311c  mov al, [ebp-5]
```

**表有 16 项（索引 0–15）；越界返回 `0x20`（空格）。**

---

## 4. 选表（@ `0x100032e0`）

```asm
0x100032f0  movzx eax, byte ptr [ebp+8]   ; method
0x100032f4  test eax, eax
0x100032f6  jl   0x10003319               ; < 0 → 失败
0x100032fc  cmp  ecx, 2
0x100032ff  jge  0x10003319               ; >= 2 → 失败
0x10003308  mov ecx, dword ptr [edx*4 + 0x10031150]   ; 从表取
0x1000330f  mov dword ptr [eax + 4], ecx  ; obj[+4] = 表指针
```

**方法号只能是 0 或 1。**

### 表 @ `0x10031150`（4 项）

| idx | 值 |
|---|---|
| 0 | `0x100293D0` |
| 1 | `0x100293BC` |
| 2 | `0x1002A1F0`（zlib） |
| 3 | 0 |

### 两个 16 字节表（实测字节）

```
表0 @ 0x100293D0: 51 49 4b 4a 48 4d 4e 41 45 54 4f 47 44 43 58 53
                 = "QIKJHMNAETOGDCXS"
表1 @ 0x100293BC: 51 53 50 45 44 49 4b 4a 48 4d 4e 41 54 4f 47 43
                 = "QSPEDIKJHMNATOGC"
```

**注意：两个表是同一组字母的不同排列。**

| 字母 | 表0 位置 | 表1 位置 |
|---|---|---|
| Q | 0 | 0 |
| S | 15 | 1 |
| P | — | 2 |
| E | 8 | 3 |
| D | 12 | 4 |
| I | 1 | 5 |
| K | 2 | 6 |
| J | 3 | 7 |
| H | 4 | 8 |
| M | 5 | 9 |
| N | 6 | 10 |
| A | 7 | 11 |
| T | 9 | 12 |
| O | 10 | 13 |
| G | 11 | 14 |
| C | 13 | 15 |

**表0 看似是乱序，表1 也乱序，两者不同。**

---

## 5. 尺寸关系

`GetSize`（`0x10002f50`）：

```asm
0x10002fa2  mov ecx, [ebp-4]
0x10002fa5  lea edx, [ecx + ecx + 0xa]   ; 2*size + 10
```

**编码后大小 = 2 × 原大小 + 10。**

这解释了为什么每个 `.ff` 载荷的 `IWff` 头之后是 `2×明文+10` 的长度。

---

## 6. 这是什么算法

**不是加密，是可逆的"半字节扩展编码"。**

特征：
- 一个字节 → 两个字符
- 每个字符来自 16 字符表
- 表只有 16 个**大写字母**
- 越界返回空格

**这不是密码学意义上的加密**（没有密钥派生、没有轮函数）。

它更像是：
- **字符集转换**（binary ↔ 16 字母表）
- 或 **一种混淆/编码**（Anti-debug）

---

## 7. ★ 但这解释不了 `.ff` 的 7.9998 熵

如果 `.ff` 载荷是用这个编码的，那它的字节应该**只来自 16 个字母**。

实测 `.ff` 载荷：**256 个不同字节值全部出现，均匀分布。**

**所以：**
- `CCoderRWFilter` 编码的是**别的数据**
- 或者 `.ff` 载荷在进入 VFS 前**已经被别的东西加密了**

---

## 8. 结论

| 项 | 状态 |
|---|---|
| 对象布局（8 字节，+4 是表指针） | **确定** |
| 算法（半字节 → 查表 → 2 字节输出） | **确定** |
| 表数量（2 个，方法号 0/1） | **确定** |
| 两张表的字节 | **确定**（已抄录） |
| 尺寸公式 `2n+10` | **确定** |
| 是否用于 `.ff` 载荷 | **否**（熵不匹配） |
| 真正的 `.ff` 加密算法 | **仍未找到** |

---

## 9. 下一步

1. 找 `ICreateZlibRWFilter` 的反向（别的过滤器）
2. 找 `.ff` 载荷在**写入 VFS 之前**的那一层
3. 检查 `IFS2.dll` 的 `CreateDebugInterface` 是否承载真正的解密
