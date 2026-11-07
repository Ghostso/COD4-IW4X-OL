# 172 · 字符串表分块扫描、链遍历、节点铸币者归因、硬件写断点

## 一、范围

本报告学习 `ClientAnimtreeHook.cpp` 240–440 行。

## 二、`scanChunk` 的三态返回

```cpp
1  = 找到，sid 有效
0  = 本块没有
-1 = 跑出了表（fault）
```

块内循环：

```cpp
rec = table + StringStride * i;
if (!*(uint16*)rec) continue;          // refcount 0 → 死槽
n = (const char*)(rec + 4);
k = 0; while (k < nameLen && n[k] == name[k]) ++k;
if (k == nameLen && !n[k]) { sid = i; return 1; }
```

**两个条件**：前 `nameLen` 字节全等，**且** 紧随其后的字节是 NUL —— 与 `PlayerDataDef::nameEquals` 的同一条规则（防止前缀误匹配）。

**只比 `nameLen` 字节而不是整串**，因为 `name` 来自调用者、长度已由 `walkChain` 截到 ≤63。

## 三、`walkChain` 的块循环

```cpp
Chunk = 256;
for (base = 0; base < 65536; base += Chunk) {
    r = scanChunk(strTable, base, base+Chunk, name, nameLen, sid);
    if (r == 1) break;
    if (r < 0) break;        // end of the table
    scanned = base + Chunk;
}
```

**`r < 0` 被解释为"表结束"**——因为字符串表是**连续分配**的，跑出末尾就是末尾。这是用 fault 当边界信号，而不是靠一个 count 字段。

扫描上限 **65536** 项（`0x10000`），与 `PlayerDataDef` 的 offset 表规模同一个数量级。

### 3.1 未命中时打印**实际指针**

```cpp
std::snprintf(out, cap,
    "sid=none scanned=%u module=0x%08X strTable=0x%08X kind=%u",
    scanned, (uintptr_t)module, (uintptr_t)strTable, kind);
```

注释：

> **报告【实际指针】而不是猜为什么扫描没找到**：一个错误的模块基址与一张在解析时刻还没被填充的表**从"没找到"这一个现象上看起来完全一样**。

这是"日志要带可区分的事实"的又一个实例。

## 四、`walkChainInner`：桶 → 链 → 条目

```text
bucketIndex = ((kind * 101) + sid * 2) & 0xFFFF
key         = ((kind << 16) | (sid >> 8))
slot        = *(u16*)(module + BucketsRva + bucketIndex*2)
entry       = module + RegistryRva + ((kind & 1) * 4096 + slot) * 16
    +0  value (u32)
    +4  next  (u16)
    +8  key   (u32)
count       = value > 0x10000 ? *(u32*)value : 0
```

### 4.1 `(kind & 1) * 4096` 是 bank 选择

注释（在常量声明处）说 registry 是"每 bank 4096 项"。所以**`kind` 的最低位选 bank**，而 `kind` 的高位参与 key 与 bucket。这是一个把"类型"和"存储区"混在同一个数里的设计。

### 4.2 遍历的三重上限

```cpp
depth < 16              最多 16 步
used + 72 < cap         输出缓冲预留
slot != 0               链尾
```

`72` 是单条输出片段的最大长度预算——**先检查再 `snprintf`**，避免截断。

### 4.3 `value > 0x10000` 才当指针解引用

```cpp
if (value > 0x10000u) count = *(uint32*)value;
```

即：**小整数不是指针**。这是把一个"值"字段同时用作"可能是指针"的判定，所以必须有个下界。`0x10000` 是保守选择（低 64 KiB 在 Windows 上不可映射）。

`entryKey == key` 时输出 `" KEYMATCH"`——**把匹配与否直接标在行里**，而不是让读的人自己比。

## 五、`readAssetSize`：重复加载器自己的查找

```cpp
asset = findAsset(36, path);        // 资产类型 36 = animtrees/<name>.atr
if (!asset) return 0;
out = *(u32*)((uintptr_t)asset + 8);
```

注释：

> **重复加载器自己的查找并读取大小字段。**

`+8` 与头文件里 `v4 = *(DWORD *)(asset + 8) + 1` 一致。

`findAsset` 是**运行时绑定的函数指针**（`FindAssetFn`），不是硬编码 RVA 的调用——因为它是 `EngineBindings` 的成员，需要模块基址。

## 六、`logNodeKey`：没有它分不清"线上驱动"与"克隆"

```cpp
extern "C" void __cdecl logNodeKey(key, asset, parent, caller)
{
    if (key < 3) return;                       // key 0 与 2 是正常的
    if (allocLogged.fetch_add(1) >= 4000) return;

    rva = caller - 0x400000;
    site = rva == 0x38731C+5 ? "clone7872D0" :
           rva == 0x3886F8+5 ? "root7886D0"  :
           rva == 0x38878C+5 ? "anc7886D0"   :
           rva == 0x38888F+5 ? "leaf7887E0"  :
           rva == 0x38A097+5 ? "clone78A050" : "?";
    ...
}
```

### 6.1 为什么必须区分

> **没有这个，日志无法分辨一次线上驱动的铸币（`sub_7887E0`，key = `record+20`）与一次克隆（`sub_7872D0`，key 从源节点复制）——而这个区分就是整个问题。**

即：`key 112` 若是**线上带过来的**，说明线能带更大的 key；若是**克隆时复制的**，说明线上只带 0/2 而 112 是本地生成的。**同一个观察值，两种截然不同的结论。**

### 6.2 `+5` 的含义

五个比较都是 `rva == <callRva> + 5`。`call` 指令是 5 字节，所以**返回地址 = 调用点 + 5**。这是 x86 的基本事实，但写出来让读者不必自己推。

### 6.3 `extern "C"` 与 `__cdecl`

因为它是从 **naked thunk** 里被调用的（`call logNodeKey`），所以不能用 C++ 名字修饰。

### 6.4 `allocLogged.fetch_add(1) >= 4000`

**先加再判**：`fetch_add` 返回旧值，`>= 4000` 时不再记录。所以最多 4000 行。**与 `record()` 里的 `ReportsPerEntityState = 64` 是同一种"按对象封顶"的纪律。**

## 七、`watchVeh`：单步异常处理

```cpp
if (info->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
    return EXCEPTION_CONTINUE_SEARCH;
eip = info->ContextRecord->Eip;
if (watchHits.fetch_add(1) < 12) { log eip }
info->ContextRecord->Dr7 = 0;               // 解除武装
return EXCEPTION_CONTINUE_EXECUTION;
```

### 7.1 三条关键

1. **只处理 `EXCEPTION_SINGLE_STEP`**，其他一律 `CONTINUE_SEARCH` —— 这个 VEH 不能吞掉别人的异常；
2. **记录 faulting EIP** —— 那就是写者的地址；
3. **清 `Dr7` 解除武装** —— "让一次写者不会把日志冲垮"。

`EXCEPTION_CONTINUE_EXECUTION` 而不是 `CONTINUE_SEARCH`：**单步异常处理完必须让原指令继续执行**，而 `Dr7` 已清所以不会再触发。

### 7.2 `watchHits < 12` 与"永不解除 DR0"

注意：只清 `Dr7`（控制寄存器），**没有清 `Dr0`**（地址）。因为 `Dr7` 是启用位，清了就不再触发。

### 7.3 那段 `[esp+36]` 的注释

```text
[esp+36] 是返回到调用我们的那个调用点的返回地址 ——
pushad(32) + pushfd(4) 在 thunk 自己的返回槽之上。
```

即：naked thunk 里 `pushad`（32 字节）+ `pushfd`（4 字节）= 36，所以 **`[esp+36]` 是 thunk 的返回地址**，也就是"谁调了 alloc"。这是 `logNodeKey` 第四个参数 `caller` 的来源。

## 八、关键结论

1. **fault 可以当作边界信号**：字符串表连续分配，跑出末尾就是末尾，所以 `r < 0` 直接 break。
2. **未命中要打印实际指针**，因为"错误基址"与"表未填充"从"没找到"上不可区分。
3. **小整数不是指针**：`value > 0x10000` 才解引用。
4. **同一个观察值可以有两种成因**（线上驱动 vs 克隆复制），所以日志必须记录**铸币者**而不只是关键词。
5. **VEH 只认自己那一种异常码**，其余一律 `CONTINUE_SEARCH`。
6. **单步断点处理完要 `CONTINUE_EXECUTION` 并清 `Dr7`**，否则会无限重触发或吞掉程序。

## 九、未闭合点

- `sub_5400B0` 用哪个数组填充命令记录（12.116.3）仍未闭合。
- 519 vs 123 的归因结论未在本组出现。
- `armWriteWatch` 的 `Dr0` 安装部分（440 行之后）未在本组读取。
