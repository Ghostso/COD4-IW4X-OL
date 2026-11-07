# CODOL 明文解密项目 (使命召唤OL / 完全可复现)

> 建立时间：2026-10-02
> 原则：**所有结论均可由原始字节复算**。不引用任何先前叙述性文档。
> 本目录内所有数字均由 `tools/codol_ff_decrypt.py` 从 `COD OL\main\*.ff` 原始文件重新算出。

---

## 1. 结论摘要（先看这里）

| 层级 | 状态 | 内容 |
|---|---|---|
| **L0 文件头** | ✅ **已解** | 21 字节 `XFileHeader`（magic/version/language/filetime），明文 |
| **L1 AES 层** | ✅ **已解** | AES-192-CTR，密钥由 RSA-2048 解封，**10/10 文件全部成功** |
| **L1 容器头** | ✅ **已解** | `IWffs100` 容器 + zone 名称（明文，**与文件名 100% 吻合**） |
| **L2 数据体** | ⚠️ **未解** | `0x14C` 之后的流。**不是** zlib/gzip/bz2/lzma，**不是**随机，**不是**重复密钥流 |

**L1 已产出完全明文**：容器头、zone 名称、全部结构字段均已解出。
**L2 仍是开放问题**，但已用统计手段将其性质收窄到很小的范围（见 §5）。

---

## 2. 文件布局（逐字节验证）

```
偏移      长度   内容
-------  -----  ------------------------------------------------
0x000      8    'IWff0100'       ASCII，明文，所有文件一致
0x008      4    u32 version      = 461 (0x1CD)，CODOL 专用
0x00C      1    u8  language     = 1
0x00D      4    u32 filetime_hi
0x011      4    u32 filetime_lo
============================== 21 字节 = XFileHeader ============
0x015    256    RSA-2048 PKCS#1 v1.5 加密的密钥块
============================== 0x115 = 密文起点 =================
0x115      -    AES-192-CTR 密文
```

### 明文（未加密）容器结构（L1 解密后）

```
偏移      长度   内容
-------  -----  ------------------------------------------------
0x000      8    'IWffs100'       明文 magic
0x008      4    u32 = 0          明文，10/10 文件均为 0
0x00C     16    (中间字段)
0x01C      -    填充
0x120     12    per-zone 元数据  每文件不同
0x12C      -    zone 名称         ASCII，NUL 填充到 16 字节  ← 明文
0x13C     16    全零             10/10 文件一致
0x14C      -    不透明数据流      ← L2 开放问题
```

**`0x12C` 处的 zone 名称是本项目的强自校验**：解出的名称与文件名逐一吻合：

| 文件 | 解出的 zone 名 |
|---|---|
| `mp_playlists.ff` | `mp_playlists` |
| `development_mp.ff` | `development_mp` |
| `localized_ui_mp.ff` | `localized_ui_mp` |
| `ui_mp.ff` | `ui_mp` |
| `code_post_gfx_mp.ff` | `code_post_gfx_mp` |
| （其余 5 个同样吻合） | — |

---

## 3. 密钥来源与验证

### RSA 私钥
1191 字节 PKCS#1 `RSAPrivateKey` DER，**与 IW4X 客户端源码中硬编码的
`FastFiles::ZoneKey` 完全相同**：
`IW4X\Client核心代码\iw4x-client\src\Components\Modules\FastFiles.cpp`

CODOL 复用了这把 IW4X 密钥。DER 解析后校验 `n == p*q` 通过。

### 解封出的 AES 密钥（**全部 10 个文件共用同一把**）

```
key = da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5   (24 字节 = AES-192)
iv  = 每文件不同，= RSA 明文载荷的 [24:40]
```

### CTR 模式
libtomcrypt `ctr_start` / `ctr_decrypt` 语义：
整个 16 字节计数器块按 **little-endian 递增**，初始计数值 == IV。

**验证方式（决定性）**：`raw[0x11D:0x121]` 在三个不同文件中分别为
`b4253d8d` / `b15a8b3a` / `b8df1983`，但解密后**全部**变成 `00 00 00 00`。
这证明密钥流正确抵消了不同密文 —— AES-CTR 参数完全正确。

---

## 4. 复现方法

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL

# 解密全部 10 个 zone，输出 layer1 明文字节
python -X utf8 _PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py "COD OL\main" --out _PLAINTEXT_PROJECT\out

# 机器可读结果
python -X utf8 _PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py "COD OL\main" --json
```

依赖：Python 3.10+ 与 `pycryptodome`（本机 3.11.9 / 3.23.0 已验证）。
脚本为**只读**：不触碰运行中的进程，不联网。

---

## 5. L2（数据体）当前证据

`0x14C` 之后的流已经用以下手段收窄：

| 假设 | 检验 | 结果 |
|---|---|---|
| zlib / raw-deflate | 全偏移扫描 + 对齐扫描 | ❌ 无有效流 |
| gzip | 全偏移扫描 | ❌ 仅随机碰撞 |
| bz2 / lzma | 直接尝试 | ❌ 异常 |
| 重复密钥流 | 自相关 lag 1..4096 | ❌ 无（H≈7.88） |
| 二次 AES 加密 | 用同一 key 多种 IV 再解 | ❌ 熵**升高**到 7.996 → 排除 |
| 位打包 6-bit | 高半字节分布 | ❌ 分布平坦 |

### 关键统计发现（真实字节偏置 = 非随机）

| 样本 | H | `<0x40` 占比 | `≥0x80` 占比 |
|---|---|---|---|
| 真实 `mp_playlists` body | 7.9760 | **28.95%** | **41.64%** |
| `os.urandom` 参照 | 7.9964 | 24.86% | 50.01% |

真实数据低字节**明显富集**、高字节**明显贫乏** → 存在真实字节偏置，**不是纯随机**。

### 熵随文件大小单调上升（压缩未达渐近的典型特征）

| 文件 | 大小 | body 熵 |
|---|---|---|
| `common_mp_reload` | 24.6 KB | 7.9189 |
| `mp_playlists` | 49.2 KB | 7.9760 |
| `development_mp` | 57.4 KB | 7.9824 |
| `code_pre_gfx_mp` | 73.8 KB | 7.9886 |
| `localized_ui_mp` | 147.6 KB | 7.9965 |
| `ui_mp` | 29.2 MB | 7.9998 |

### 已定位的固定明文结构

- `body[0:4]` = `00 00 00 00` —— **6/6 文件一致**
- `body[4:8]` 每文件不同
- `0x13C` 处 16 字节全零 —— 10/10 文件一致
- zone 名称固定落在 `0x12C`

### L2 的下一步（按可行性排序）

1. **在真实客户端内定位 L2 解码函数**：`Zones.cpp` 已给出权威线索 ——
   `Game::Load_Stream` / `DB_ReadXFile` / `DB_ReadXFileUncompressed`
   是三条不同读取路径，L2 变换就在其中。
2. **运行期 dump**：在 `DB_LoadXAssets` 完成后 dump zone 内存，
   与 L1 输出逐字节比对 —— 可直接得到 L2 的逆变换结果。
3. **对比 IW4X 的 `ZoneBuilder.cpp` / `ZoneConvert.cpp`**（49 KB / 66 KB）：
   它们实现了 zone 的**写入**方向，是 L2 编码的现成参考实现。

---

## 6. 产物清单

| 路径 | 说明 |
|---|---|
| `tools/codol_ff_decrypt.py` | 独立解密器（L0+L1），含自校验 |
| `out/*.layer1.bin` | 10 个 zone 的 L1 明文字节 |
| `evidence/layer1_evidence.json` | 逐文件指纹：SHA-256、熵、偏移、密钥 |
| `README.md` | 本文档 |

---

## 7. 纪律（沿用本项目既有规则）

- 禁止 `sc stop/config/delete` ACE 驱动 → **实测蓝屏 `0x01010002`**
- `.ps1` 必须纯 ASCII（PS 5.1 按 GBK 读取，中文字面量会乱码）
- `.tvm0` / `.vmp0` 段内代码是加密的，capstone 反汇编一律垃圾，**不得据此下结论**
- 字符串存在 ≠ 存在可达分支
