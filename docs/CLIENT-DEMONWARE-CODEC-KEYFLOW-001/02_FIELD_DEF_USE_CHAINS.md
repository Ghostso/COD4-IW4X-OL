# 02 字段 def-use 链

## 0. 字段语义（本轮更正上轮的两处错标）

| 字段 | 上轮报告标注 | 本轮确证 | 依据 |
|---|---|---|---|
| `this+0x5F0` | "密码学 provider 候选位置" | **AES/加密 provider 对象指针**（`operator new(0x394)` 构造，vtable `0x00C5A31C`） | `0xAAB95D`/`0xAAB983` |
| `this+0x5F4` | 同上 | **AES/解密 provider 对象指针**（同类型，独立实例） | `0xAAB9BD`/`0xAAB9E3` |
| `this+0x5F9` | "codec 输出候选位置" | **20B codec 暂存区 `[+0x5F8, +0x60C)` 的写法定址常量**（`0xAA8E3C add eax,0x5F9`；循环中 `[eax-1]` 是首字节，故真实首字节为 `+0x5F8`） | `0xAA8E3C` |
| `this+0x60D` | 同上 | **20B codec 暂存区 `[+0x60C, +0x620)` 的写法定址常量**（`0xAA8CBD add eax,0x60D`；真实首字节为 `+0x60C`） | `0xAA8CBD` |

即：两个 **20 字节** 缓冲区连续存放，整体覆盖 `[+0x5F8, +0x620)`；`0x5F9`/`0x60D` 是"基址+1、循环内以 `[eax-1]` 访问首字节"这一写法定址下的地址常量。（上一轮报告称之为"输出位置"，措辞不准确但不影响其结论。）

## 1. Codec A 输出链（`data[0:20]` → HMAC 请求密钥）

```text
[def] 0x00AAB911  call expandKey(secret,"BDDATA",72)  -> [ebp-0xA8]  (72B)
         └ 0x00AAB8FB push 0x48 / 0x00AAB906 push 0xC5B13C / 0x00AAB910 push 0x14
[def] 0x00AAB92C  call 0xAA8D70(dl=1, &[ebp-0xA8])     -> mem[this+0x5F8 .. this+0x60B]   (20B, STORE)
[use] 0x00AAACE3  call 0xAA8D70(dl=0, &[ebp-0x24])     -> [ebp-0x24] = mem[this+0x5F8 .. this+0x60B]  (LOAD)
         └ 0x00AAACE8 push 0x14 (20) / 0x00AAACEE HMAC_SHA1 上下文 0xDF6216D
[use] 0x00AAAD40  call 0xA88400  HMAC_Update(ctx, frame, len-8)
[use] 0x00AAAD??  HMAC_Final -> 8B tag 写入发送缓冲
```

调用点位置说明：`0x00AAACE3` 位于**出站 0x85 组帧之前**（`0x00AAAA10` 函数的发送分支）；`0xAAAD40` 的 `HMAC_Update` 参数 `len = [ebp-0x208]-8` 与帧长口径一致（tag 占末 8B）。

## 2. Codec B 输出链（`data[20:40]` → HMAC 应答密钥）

```text
[def] 0x00AAB911  call expandKey(secret,"BDDATA",72)  -> [ebp-0xA8]  (72B)
[def] 0x00AAB93C  call 0xAA8BF0(dl=1, &[ebp-0x94])     -> mem[this+0x60C .. this+0x61F]   (20B, STORE)
         └ 0x00AAB933 lea edx,[ebp-0x94]  (= data[20:40])
[use] 0x00AAB046  call 0xAA8BF0(dl=0, &[ebp-0x40])     -> [ebp-0x40] = mem[this+0x60C .. this+0x61F]  (LOAD)
[use] 0x00AAB04B push 0x14 (20) / 0x00AAB051 HMAC_SHA1 上下文 0xDF6216D
[use] 0x00AAB085 call 0xA88400  HMAC_Update(ctx, 入站帧, len-4)
[use] tag 比较 0x00AAB0E6–0x00AAB12B（8B XOR/OR 归并）
```

`0x00AAB046` 位于**入站 0x85 帧解析函数 `0x00AAAE70`** 内（`= 0xAAAE70+0x1D6`）。

## 3. 其他四个字节范围（不经 codec）

同一 `expandKey(...,"BDDATA",72)` 输出的**后半** 32 字节被直接切分并送入 AES provider，**完全不经 codec**：

```text
[def] 0x00AAB911  data[72] -> [ebp-0xA8]
[use] 0x00AAB941  mov ecx,[edi+0x5F0]          ; 旧 provider（若有）-> 虚表[0] 析构
[def] 0x00AAB96A  0xDF9AA45(0x394) + 0xA87BA0  ; 构造 provider #1 -> [edi+0x5F0]
[use] 0xAAB989-0xAAB99A  provider#1.vtbl[1](&[ebp-0x80], 0x10)   ; 取 16B **密钥**
         └ &[ebp-0x80] 在 0xAAB9F8 同址出现，对应 data[40:56]
[def] 0x00AAB9C2  0xDF9AA45(0x394) + 0xA87BA0  ; 构造 provider #2 -> [edi+0x5F4]
[use] 0xAAB9ED-0xAAB9FE  provider#2.vtbl[1](&[ebp-0x70], 0x10)   ; 取 16B **密钥**
         └ &[ebp-0x70] = data[56:72]
```

`0xAAB98B mov edx,[edx+4]`（vtable 槽 1）+ `push 0x10` + `push &local` → 即 `provider->setKey(buf, 16)`；对应 vtable `0x00C5A31C` 的槽 [1] = `0x00A87C30`。该函数体内 `0xA87C65` 起对 `[0xC5BEB4]`（cipher 名索引）与 `edi+8`（keylen）赋值，`0xA87C92` 把 16B 密钥拷入 provider 内部 `+0xC`。**未触及 `+0x5F9`/`+0x60D`**。

provider 的对象大小与存活期：

- 每次 KDF 都**先析构旧 provider**（`0xAAB94B`/`0xAAB9AB` 经 vtable[0]），再 `0x394` 字节重建（`0xDF9AA45` + `0xA87BA0`）。
- 会话重置/析构路径（`0xAAA14D`–`0xAAA177`、`0xAAA6E9`–`0xAAA6FB`）会把 `+0x5F0`/`+0x5F4` 置 0 并逐个析构。
- **`+0x5F8`/`+0x60C` 两个 20B 缓冲不在 provider 内**：provider 是独立堆对象（指针存于 `+0x5F0`/`+0x5F4`），而 codec 暂存区在**会话对象本体**内。

## 4. 完整写入点清单（`.text` 全节，指令级编码扫描）

| 字段 | 写入点 | 语义 |
|---|---|---|
| `+0x5F0` | `0xAAA6E9`（=0，重置）、`0xAAB983`（新对象） | provider #1 指针 |
| `+0x5F4` | `0xAAA6EF`（=0，重置）、`0xAAB9E7`（新对象） | provider #2 指针 |
| `+0x5F8..0x60B` | `0xAA8E44`–`0xAA8EC9`（Codec A，仅 STORE 分支，经 `+0x5F9` 基址） | 20B codec A 暂存 |
| `+0x60C..0x61F` | `0xAA8CC5`–`0xAA8D4A`（Codec B，仅 STORE 分支，经 `+0x60D` 基址） | 20B codec B 暂存 |
| `+0x5E8/+0x5EC` | `0xAAB8E0`/`0xAAB8E7`（challenge[8:16]，`edx`/`ecx` 两个 dword 直写） | 应答 ID，**不经 codec** |
| `+0x620/+0x624` | `0xAAB3A6`（入站 8B）、`0xAAB6BD`（入站 8B） | 0x81 帧内字段 |

**关键结论**：`+0x5F8`/`+0x60C` 的**唯一写入者**是 codec STORE；其**唯一读取者**是 codec LOAD（`+0x5F8` 的读取点即 Codec A LOAD 分支 `0xAA8E88`–`0xAA8EB9`；`+0x60C` 的读取点即 Codec B LOAD 分支 `0xAA8D09`–`0xAA8D3A`）。全 `.text` 内没有第三个函数读写这两个范围。

## 5. 生命周期

```text
会话对象构造/重置  0xAAA6E9/0xAAA6EF  +0x5F0=+0x5F4=0
握手 0x81 到达     0x00AAB310
  ├ STORE codec A -> +0x5F8..+0x60B
  ├ STORE codec B -> +0x60C..+0x61F
  ├ 新建 provider #1/#2 -> +0x5F0/+0x5F4（用 data[40:56]/[56:72]）
  └ 写入 +0x5E8/+0x5EC = challenge[8:16]
出站 0x85          LOAD codec A -> HMAC key（+0x5F8 仍有效）
入站 0x85          LOAD codec B -> HMAC key（+0x60C 仍有效）
会话重置/析构       0xAAA14D/0xAAA165 析构 provider，+0x5F0/+0x5F4=0
```

`+0x5F8`/`+0x60C` 在会话存活期间**不被清零、不被其他逻辑覆写**（无 `+0x5F8`/`+0x60C` 的写入点，除 codec STORE 外）。因此 LOAD 读到的必然是握手期 STORE 写入的同一 20B。

## 6. 证据等级

| 结论 | 等级 |
|---|---|
| 字段语义更正（+0x5F0/+0x5F4 = provider 指针；+0x5F9/+0x60D = 20B 暂存的基址常量） | PROVEN |
| Codec A/B 各自 STORE→LOAD 成对 | PROVEN |
| `+0x5F8`/`+0x60C` 唯一写入者 = codec STORE | PROVEN（指令级编码扫描 + 边界校验） |
| 后半 32B（`data[40:56]`/`[56:72]`）不经 codec 直接作 provider 密钥 | PROVEN（`0xAAB98E`/`0xAAB9F6`，`push 0x10`） |
| `+0x5E8/+0x5EC` 不经 codec | PROVEN（`0xAAB8E0`/`0xAAB8E7` 直写） |
| 会话重置/析构路径 | PROVEN（`0xAAA14D`–`0xAAA177`） |
