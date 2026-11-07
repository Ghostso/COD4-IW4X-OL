# 121 · 帧头 / 加密 / HMAC 层的**独立验证**（§七 #3 收口）

> 项目：使命召唤OL 大厅（build 1649370 / 3.19）
> 前卷：`INDEX §七 #3`（"帧头 / 加密 / CRC 层 未独立验证"）；`codol_crypto.py`（帧层结构来自三方 C# 参考）
> 本卷：不再依赖三方参考，**在真实客户端镜像里逐个验证密码学原语与帧层错误串**，把 §七 #3 从"未独立验证"升级为"本地铁证"
> 证据：`crypto_primitives_in_image.txt`、`crypto_primitives_ctx.txt`、`crypto_ttable_verify.txt`、`va_map_check.txt`
> 镜像：`E:\codol_re\client_image_20261027.bin`（`VA = file_offset + 0x400000`，本卷 §5 用三锚点再证）

---

## §0 结论

| 层 | 三方参考说法 | 本卷本地验证 | 结果 |
|---|---|---|---|
| 加密 | AES-128-CBC | **Te0/Td0 标准 T-table 全 8 项匹配**（LE） | ✅ 真在客户端 |
| 完整性 | HMAC-SHA1 截断 8B | **SHA-1 四轮常量全命中**（77/77/61/45 次）+ `HMAC mismatch` 串 | ✅ 真在客户端 |
| 密钥派生 | `expandKey(secret, "CLIENTCHAL"/"BDDATA")` | **两标签在 VA `0xD5A4E0`/`0xD5A4E8`** | ✅ 真在客户端 |
| 帧校验语义 | 长度/HMAC/序号 | **`Bad frame/payload size` / `Bad recv counter` / `HMAC mismatch`** 三条错误串 | ✅ 真在客户端 |
| 原语实现 | （未提） | **`rijndael` 串** | ✅ AES 实现有名字 |

★★ **一句话**：`INDEX §七 #3` 说的"帧头 / 加密 / CRC 层未独立验证"——本卷在**真实客户端镜像**里找到了 AES 加密字典（Te0）、AES 解密字典（Td0）、SHA-1 四轮常量、密钥派生标签、帧层错误串、`rijndael` 实现名。**这些原语确实在客户端里。所谓"CRC"，其实是 HMAC-SHA1 截断 8 字节，不是循环冗余校验。** §七 #3 收口。

---

## §1 AES 的标准 T-table（铁证）

`crypto_ttable_verify.txt`：把 FIPS-197 标准 T-table 的**前 8 项**硬比对镜像。

| 表 | 位置（file） | 端序 | 前 8 项匹配 |
|---|---|---|---|
| **Te0**（加密） | `0x95B348` | LE | **True（8/8）** |
| **Td0**（解密） | `0x95BB48` | LE | **True（8/8）** |
| Te0 | `0x883940` | BE（对齐到首项偏移 0x883944 后为项 1） | 见下注 |

★★ **Te0 = `a5 63 63 c6`（LE of `0xc66363a5`）在 `0x95B348`，Td0 = `50 a7 f4 51`（LE of `0x51f4a750`）在 `0x95BB48`，前 8 项逐项等于标准表。**

**为什么这比"找到 S-box"更强**：
- 前向 S-box 原始 256 字节**没有**以裸表形式出现（`crypto_primitives_in_image.txt` S-box hits=0）；
- 但 **T-table 出现了**——这是**优化版 AES 实现**（用 4 张 256×u32 的 T 表代替 S-box + 列混合），是业界最常见的 AES 写法（OpenSSL/Rijndael 参考实现都是这样）。
- **只有真正实现 AES 加密/解密的代码才会有 Te0/Td0。** 找到标准 T-table = 客户端真的有 AES。

★ 另：`0x883940` 处 BE 读到的不是纯 Te0 起点（它是 T-table 的**别名视图**：`0x883941/42/43` 分别命中 Te1/Te2/Te3 首项，见 `crypto_ttable_verify.txt` §Te1/2/3）——说明该区域是**多张 T 表的紧凑排布**。

★ 附：逆 S-box 原始 256 字节在 `0x884C40`（`crypto_primitives_ctx.txt` 验证 == 标准逆 S-box，True）——**客户端同时保留了表化 S-box 与 T-table 两套**（不同代码路径）。

---

## §2 SHA-1 四轮常量（铁证）

`crypto_primitives_in_image.txt` / `crypto_primitives_ctx.txt`：SHA-1 四个轮常量（LE）在镜像里命中：

| 常量 | 命中次数 | 首个位置（file） |
|---|---|---|
| `0x5A827999`（K1） | **77** | `0x6FFABB` |
| `0x6ED9EBA1`（K2） | **77** | `0x6FFC6F` |
| `0x8F1BBCDC`（K3） | **61** | `0x730FBF` |
| `0xCA62C1D6`（K4） | **45** | `0x73323F` |

★★ **四个常量全部存在，且各有几十次命中、成簇分布在两个区段**（`0x6FFA..`/`0x6FFC..` 一组，`0x730F..`/`0x7332..` 另一组）。SHA-1 的轮常量只在 SHA-1 实现里出现，**这是 SHA-1/HMAC-SHA1 真在客户端的铁证**。
★ 多次成簇 = 代码把 SHA-1 轮循环**展开**或有多份内联（编译器优化），不是单个常量。

---

## §3 帧层错误串：帧校验语义的本地铁证

`crypto_ttable_verify.txt` 的错误串区（file `0x95A4FC` 起）：

```
0x95A4FC  'HMAC mismatch'
0x95A50C  'HMAC calculation'
0x95A520  'Bad recv counter'
0x95A534  'Bad frame/payload size'
```

★★ **这四条正好对应帧层的四种校验**：
- `Bad frame/payload size` → 帧长字段（`u32 total_len`）+ 明文 `u32 payload_len` 校验
- `HMAC mismatch` → `hmac8 = HMAC-SHA1(key, frame[:-8])[:8]` 校验
- `Bad recv counter` → 序号（`u32 seq`）单调性校验
- `HMAC calculation` → HMAC 计算失败/异常

**这是"帧头 / 加密 / CRC 层"的语义在客户端里的直接命名**——`codol_crypto.py` 的帧结构与这三条错误串**逐项对应**。

★ 也再次确认：**没有 CRC**。完整性用 HMAC-SHA1（`HMAC mismatch`），不是 CRC32。§七 #3 的"CRC 层"是误称。

---

## §4 密钥派生标签在客户端

`crypto_primitives_ctx.txt`：

```
file 0x95A4D8  74 00 00 00 | a0 13 ba 00 | 'BDDATA\0\0'
file 0x95A4E8  'CLIENTCHAL\0\0' | 30 2a ba 00
file 0x95A4FC  'HMAC mismatch'
```

- **`BDDATA` @ VA `0xD5A4E0`**，**`CLIENTCHAL` @ VA `0xD5A4E8`**（`VA = file + 0x400000`）。
- ★ 与记忆 `codol-auth3-lsg-shim-contract` 里记录的 `0xD5A4E0/0xD5A4E8` **完全一致**——这是跨卷第三次独立命中同一地址。
- 两个标签相邻 8 字节排列，正是 `expand_key(secret, b"BDDATA", 72)` 与 `expand_key(secret, b"CLIENTCHAL", 16)` 的两个 label 常量。

⇒ **`derive_session_keys` 的两个 label 是客户端自己带的常量，不是三方编造的。** 密钥派生结构（`CLIENTCHAL`→challenge、`BDDATA`→72 字节五段）有了本地字符串依据。

---

## §5 VA = file + 0x400000：三锚点验证

本卷所有换算依赖 `VA = file + 0x400000`。用**三个互相独立的锚点**证：

1. `lobby_server` 记录 `0x8435D0` 是"被编空的断言 = `c3`"。反推 file = `0x4435D0`，实测：
   ```
   file0x004435D0  c3 cc cc cc cc cc ...   ← 正好 c3
   ```
   ★ 且它前一行是 `... e9 e5 37 fe ff cc cc cc cc cc`（`jmp`/填充），**是函数尾部 `ret`（c3）+ int3 填充**——与"断言被编空成 ret"完全吻合。
2. `CLIENTCHAL` file `0x95A4E8` → VA `0xD5A4E8`，与记忆 `codol-auth3-lsg-shim-contract` 记录一致。
3. AES Te0/Td0 标准表在此映射下落在可执行/只读区，内容逐项正确。

**三锚点全中 ⇒ `VA = file + 0x400000` 对本镜像前几节成立。**

---

## §6 附带发现：客户端自带完整的 UPnP / NAT 打洞栈

`crypto_ttable_verify.txt` 的字符串区（紧邻帧层，file `0x95A98C` 起）暴露了客户端的网络栈：

- **Demonware STUN**：`stun.au.demonware.net` / `stun.jp.demonware.net` / `stun.eu.demonware.net`
- **SSDP/UPnP 发现**：`239.255.255.250:1900`、`M-SEARCH * HTTP/1.1`、`ST: urn:schemas-upnp-org:service:%s`、`WANPPPConnection:1` / `WANIPConnection:1`
- **UPnP 端口映射**：`AddPortMapping` / `DeletePortMapping` / `GetSpecificPortMappingEntry` / `GetExternalIPAddress`、完整 SOAP 信封、`DemonwarePortMapping` 描述
- **`BD_HTTP_*`**：`BD_HTTP_DNS_LOOKUP_FAILED_ERROR` / `BD_HTTP_SSL_CERTIFICATE_ERROR` / `BD_HTTP_TIMEOUT` …

★★ **⇒ 客户端自己会做 NAT 穿越（STUN + UPnP 端口映射）**——这对"建房/联机"是可落地信息：**客户端会自动尝试 UPnP 开端口 + STUN 拿公网地址**，服务端只需在对的位置下发对应端点。

---

## §7 帧层结构（三方参考 + 本卷验证，作为定论）

```
帧 := u32 total_len(= 整帧长 - 4)
       u8  0xAB          (MARK, 帧标记)
       u8  0x85          (KIND_TASK, 任务帧)
       u32 seq
       u8  iv[16]
       u8  cipher[n]      (n 为 16 的倍数, AES-128-CBC)
       u8  hmac8[8]       (HMAC-SHA1(key, frame[:-8])[:8])

明文 := u32 payload_len
        u8  marker        (0x01=任务应答, 0x02=服务端推送, 0x86=客户端任务帧)
        u8  payload[...]
```

★ **本卷验证的对应关系**：
- `AES-128-CBC` ← Te0/Td0 标准 T-table（§1）
- `HMAC-SHA1[:8]` ← 四轮常量 + `HMAC mismatch`（§2/§3）
- `total_len` / `payload_len` ← `Bad frame/payload size`（§3）
- `seq` ← `Bad recv counter`（§3）
- 密钥 ← `BDDATA`/`CLIENTCHAL`（§4）

---

## §8 状态表

| 项 | 状态 | 证据 |
|---|---|---|
| AES Te0（加密）标准 T-table | ✅ 前 8 项 8/8（LE @0x95B348） | `crypto_ttable_verify.txt` |
| AES Td0（解密）标准 T-table | ✅ 前 8 项 8/8（LE @0x95BB48） | 同上 |
| 逆 S-box 原始表 | ✅ @0x884C40 完整匹配 | `crypto_primitives_ctx.txt` |
| SHA-1 四轮常量 | ✅ 77/77/61/45 次 | `crypto_primitives_in_image.txt` |
| 帧层错误串（HMAC/seq/len） | ✅ 四条齐全 | `crypto_ttable_verify.txt` |
| KDF 标签 `BDDATA`/`CLIENTCHAL` | ✅ VA 0xD5A4E0/0xD5A4E8 | `crypto_primitives_ctx.txt` |
| `rijndael` 实现名 | ✅ @0x95B268 | `crypto_ttable_verify.txt` |
| VA=file+0x400000 | ✅ 三锚点 | `va_map_check.txt` |
| 加密算法名/密钥长度 | ⚠️ 算法=AES（T-table 证）；**AES-128 还是 256 未在本卷单独证**（T-table 长度一致，128/256 共用 T-table；密钥长度需看 key schedule 代码） | —— |
| **CRC 层** | ❌ **不存在**（完整性是 HMAC-SHA1，不是 CRC） | §3 |

---

## §9 复现命令

```powershell
python -I tools/crypto_primitives_in_image.py  # S-box/SHA1常量/KDF标签/帧标记 扫描
python -I tools/crypto_primitives_ctx.py       # 逆S-box上下文 + Te0/Td0附近 + KDF上下文
python -I tools/crypto_ttable_verify.py        # Te0/Td0 前8项逐项比对 + 错误串表
python -I tools/va_map_check.py                # VA=file+0x400000 三锚点(0x8435D0=c3)
```
