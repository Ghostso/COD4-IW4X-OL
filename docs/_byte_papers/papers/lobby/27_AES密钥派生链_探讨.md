# AES 密钥派生链 · 探讨：我误判了两次，才走到正确的链

> 对应：`lobby/27_AES密钥派生链.md`

---

## 一、第一次误判：把 zlib 当成 .ff 加载

我在 `0x483b40` 看到：

```
0x483bae  call 0x483a50      ← AES 初始化
0x483c07  call 0x791eb0
```

第一反应：**`0x791eb0` 一定是 `.ff` 加载函数**，
因为它紧跟在 AES 初始化后面。

---

## 二、反汇编 `0x791eb0`

```
0x791ebc  mov [esi+0x18], edi
0x791ec4  mov [esi+0x20], 0x794400     ← alloc 回调
0x791ed3  mov [esi+0x24], 0x794440     ← free 回调
0x791ee0  push 0x18
0x791ee2  push 1
0x791ee5  call ecx                     ← 调用 alloc
0x791efd  mov [eax+0x10], 0xf          ← 0xf
0x791f16  push 0x8000                  ← 0x8000 = 32768
0x791f1e  call 0x790950
```

**`esi+0x20` = alloc，`esi+0x24` = free，`esi+0x28` = opaque。**

这是 **zlib 的 `z_stream` 结构**：

```c
typedef struct z_stream_s {
    Bytef *next_in; uInt avail_in;
    Bytef *next_out; uInt avail_out;
    char *msg;
    struct internal_state *state;
    alloc_func zalloc;   // +0x20
    free_func  zfree;    // +0x24
    voidpf     opaque;   // +0x28
    ...
} z_stream;
```

**`0x791eb0` = `inflateInit2`。**

**不是 `.ff` 加载。**

---

## 三、第二次误判：把 SHA 上下文当构造器

我看到：

```
0x483a71  mov eax, 0x100        ← 256
0x483a76  lea ecx, [ebp-0x130]
0x483a7c  call 0x484940
```

以为 `0x484940` 是"构造一个 256 字节 SHA-256 上下文"。

**反汇编后：**

```
0x48494f  mov [0x1cd17c0], ecx     ← 保存 buffer 指针
0x484960  mov eax, [0x1cd17b8]     ← 剩余空间
0x484982  call 0xc427f0            ← memcpy
0x484995  add [0x1cd17b4], esi     ← 推进写指针
```

**这是一个 `Buffer::write(ptr, size)`。**

`0x483a76` 那两行其实是：

```
lea ecx, [ebp-0x130]     ← 目标缓冲
call 0x484940            ← (ecx=目标, eax=大小) 写入
```

**它在"准备一个 256 字节的输入缓冲"。**

---

## 四、两次误判的共同点

**都是"按位置猜功能"** ——
"这段代码在 AES 初始化后面，所以它一定是加载器"，
"这个函数被传了 256，所以它是构造器"。

**位置关系不是功能证据。**

---

## 五、正确的做法

**反汇编被调用函数本身。**

- `0x791eb0` 里出现 `alloc/free/opaque` 三件套 + `0x8000` → zlib
- `0x484940` 里出现 `memcpy + 指针推进` → Buffer::write

**两条都能在 300 行内读出来，不需要猜。**

---

## 六、修正后的链条

```
0x483b40 初始化
   ├─ 清零 zlib 结构
   ├─ rep movsd 13 dword ← 传参（52 字节）
   ├─ zlib 结构初始化
   ├─ 0x483a50  ★ 派生 AES 密钥
   └─ 0x791eb0  zlib inflateInit2
```

**所以 `0x483b40` 是"准备 zlib+AES 解压解密流"的函数。**

**这解释了 `.ff` 的处理方式：**

```
.ff 载荷 = AES 加密 + zlib 压缩
处理 = 先 AES 解密，再 zlib 解压
```

**或者反过来。**

---

## 七、这纠正了我之前的一个判断

第 16 卷我读 `IFS2.dll` 的字符串，
看到 `bzip2` 和 `compSize`，判断"压缩是 bzip2"。

**但客户端 EXE 里用的是 zlib（`inflateInit2`）。**

**两种可能：**
1. IFS 层用 bzip2，`.ff` 层用 zlib（两层不同）
2. bzip2 只在打包工具里用

**这需要再核对。**

---

## 八、方法论收获

> **"被调用"不等于"相关功能"。要读函数体。**

三次了：
- 第 15 卷：`CCoderRWFilter` 解出来但不是 `.ff` 的（用熵判据排除）
- 本卷：`0x791eb0` 不是加载器（读函数体排除）
- 本卷：`0x484940` 不是构造器（读函数体排除）

**每次都是"我以为 X 是 Y"，然后读函数体发现不是。**

**代价是：如果我不读，会写出一份错误的调用链。**

---

## 九、下一步

1. 找 `0x483b40` 的调用者（谁在准备这个流）
2. 确认 `[ebp-0x130]` 那 256 字节的来源
3. 确认 `.ff` 到底是"先解压再解密"还是"先解密再解压"
