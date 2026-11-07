# COD OL fastfile（`.ff`）解密 —— 层一已攻克，层二未闭合

日期：2026-09-30
方式：**纯离线静态 + 密码学验证**。未启动游戏、未读运行进程、未改网络。
前置参照：库内 `IW4X\Client核心代码`（IW4X 客户端源码，含 `FastFiles::ZoneKey`）。

---

## 0. 一句话结论

`COD OL\main\*.ff` 的加密链**已完整识别并实测解出层一**：
`IWff0100` 头 + RSA-2048 保护的主密钥 + AES-CTR 主体。
**RSA 私钥与 IW4X 客户端硬编码的 `ZoneKey` 完全相同**，10 个 `.ff` 全部解出
引擎容器魔数 `IWffs100`。层二（CTR 之后的容器体）仍未定性。

---

## 1. 关键突破

此前（`_subagent_cfg_crypto.md` 等）把 `config_mp.cfg` / `.ff` 的读取判定为
"在 `.tvm0`/`.tls` 里、需要绕机器安全设置"。**本轮证明 `.ff` 根本不需要运行期取证**：
解密所需的**私钥就硬编码在公开的 IW4X 源码里**，可直接离线复刻。

| 项 | 结论 | 级别 |
|---|---|---|
| `.ff` 容器格式 = IW4 DBIF（`IWff0100` 头 + RSA 密钥 + AES-CTR 体） | 已证 | HIGH |
| RSA 私钥 == IW4X `FastFiles::ZoneKey`（PKCS#1 DER，1191 字节） | 已证 | HIGH |
| 密钥块 = PKCS#1 v1.5，`k || iv` = 40 字节（AES-192 + 16B IV） | 已证 | HIGH |
| 层一（CDX + CTR）对 10/10 个 `main\*.ff` 成功 | 已证 | HIGH |
| 层一产物 = `IWffs100` 容器 + 内部 zone 名 | 已证 | HIGH |
| 层二变换 | **未证**（明确否证 zlib/deflate/gzip/lzma/bz2/ECB/CBC） | — |

---

## 2. 文件格式与算法链

```
偏移       内容
0x000      XFileHeader（21 字节，pack 1）
             magic:    'IWff0100'  (u64)
             version:  461         (u32)   ← 与 IW4X 的 XFILE_VERSION_LATEST_CODO 一致
             language: 1           (u8)    // XLANG_ENGLISH
             filetime_hi/lo: u32,u32
0x015      256 字节 RSA-2048 加密块（PKCS#1 v1.5）
0x115      主体 = AES-CTR（libtomcrypt 语义）
```

解密步骤（每一步都有字节级验证）：

1. `m = rsa_private_decrypt(blob)`，得到 `00 02 <随机非零填充> 00 <40字节>`。
2. 40 字节 payload：
   * `payload[0:24]` = **AES-192 key**
   * `payload[24:40]` = **16 字节 IV / CTR 初值**
3. `plain = AES_CTR_decrypt(body)`，计数器为**整块小端自增**，初值 = IV。

> 计数器规则已穷举确认：只有"**小端**整块自增"能解出魔数且保持结构；
> 大端 / 32 位 / 64 位变体均落在随机（熵 7.98）。

---

## 3. RSA 私钥来源：与 IW4X `ZoneKey` 同源

`IW4X\...\src\Components\Modules\FastFiles.cpp` 中：

```cpp
unsigned char FastFiles::ZoneKey[1191] = { 0x30,0x82,0x04,0xA3, ... };
...
rsa_import(FastFiles::ZoneKey, sizeof(ZoneKey), &key);
rsa_decrypt_key_ex(encKey, 256, CurrentKey.data, &outLen, ...);
ctr_start(aes, CurrentKey.iv, CurrentKey.key, sizeof(CurrentKey.key), 0, 0, &CurrentCTR);
```

该 1191 字节是标准 **PKCS#1 `RSAPrivateKey` DER**。本机自洽性校验：

```
n = p*q            True
d*e mod lcm(p-1,q-1) == 1   True
n 位宽            2048
```

⇒ 直接用它解 `.ff` 的 0x15 处 256 字节块，**PKCS#1 v1.5 结构成立**。

---

## 4. 层一实测（10/10 成功）

工具：`CODOLServer\_mainline\ff_iw4_decrypt.py`

| 文件 | 版本 | 解出 AES key | 解出 IV | 层一头 |
|---|---|---|---|---|
| mp_playlists.ff | 461 | `da135e91…c6db65` | `ff6c10c6db650000149c1f0103000000` | `IWffs100` |
| ui_mp.ff | 461 | 同 | `00a2689e11418e02b22bd822d9030000` | `IWffs100` |
| code_post_gfx_mp.ff | 461 | 同 | `cfaa386412090601efc91b5a85030000` | `IWffs100` |
| code_pre_gfx_mp.ff | 461 | 同 | `603798b08bc80000368d283c0b000000` | `IWffs100` |
| code_post_gfx_default_mp.ff | 461 | 同 | `16902856549f0000fdc1c59b23000000` | `IWffs100` |
| common_mp_reload.ff | 461 | 同 | `db1dbba9660d0000c903fcba04000000` | `IWffs100` |
| development_mp.ff | 461 | 同 | `3d20990502a1000034b493162f000000` | `IWffs100` |
| localized_code_post_gfx_mp.ff | 461 | 同 | `8302ce39df132100c06fc63768310000` | `IWffs100` |
| localized_code_pre_gfx_mp.ff | 461 | 同 | `1b932c0b2c070000c6b685b305000000` | `IWffs100` |
| localized_ui_mp.ff | 461 | 同 | `3d4526c67f1f07002888c1fc67180000` | `IWffs100` |

**两个强事实**：

1. **AES 主密钥全库唯一** = `da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5`。
   RSA 块每文件都不同（每次随机会话），但都解出同一把 key。
2. **IV 每文件不同**，且明显是结构化字段（末尾几字节多为小整数 / 零）。

解出层一的容器头形态（两种）：

```
'IWffs100' 00 00 00 00 <name>\0 ...
'IWffs100' 00 00 00 00 <len> <name>\0 ...   // code_post_gfx_mp 用这种
```

内部 zone 名可读（`mp_playlists`、`code_post_gfx_mp` …），说明层一是**真实明文流**。

---

## 5. 仍未闭合：层二

层一产物**不是**引擎可直接消费的 IW4 流：

* 标准 iw4 / IW4X 流 = `IWffu100`/`IWff0100` 魔数之后紧跟 **zlib 流**。
* COD OL 层一 = `IWffs100` 魔数 + 4 零字节 + **高熵数据**（4096B 窗口熵 ≈ 7.95）。

⇒ **`IWffs100` 是 COD OL 引擎自有的加密容器**，其体还叠加了一层变换。

### 5.1 已机械否证的层二假设

| 假设 | 检验 | 结果 |
|---|---|---|
| CTR 之后是 zlib / raw-deflate / gzip | 全流逐字节尝试 inflate | **零命中** |
| CTR 之后是 lzma / bz2 | 偏移 0..63 全试 | **零命中** |
| 计数器用大端 / 32 位 / 64 位 | 穷举 6 种 | 只有小端有结构，其余熵 7.98 |
| 层二是 AES-ECB/CBC | 相隔 4 KiB 两窗 XOR 熵 | 7.96（≈独立）⇒ **无重复密钥流** |
| 层二是明文（未压缩 zone） | 长 ASCII 串扫描 | 除 zone 名外基本无串，熵 6.3+ |
| 每 8192 字节重置 IV 的 CTR | 实试 | 头后仍高熵 |
| 层二是 `sha256(iv)` 密钥流 | 实试 | 反而破坏魔数 |

### 5.2 层二的可疑落点

引擎里 `IWffs100` / `IWff0100` / `IWffu100` 三个标识同处一个字符串池
（exe VA `0xDB5EC8` 附近：`sha256 \0 IWffs100 \0 aes \0 1.1.4 \0 IWff0100 \0 IWffu100`），
且 exe 导入表**只有一项**（`…Base.dll` 序号 1），真正的加载器在 `Base.dll`。
⇒ 层二的实现位于 `Base.dll`，而 `Base.dll` 的逻辑主体在 `.tls`（可执行高熵区）
与 `.tvm0`（VMProtect）——这是本轮**未触碰**的区域。

`config_mp.cfg`（`_subagent_cfg_crypto.md`）与本层的**结构同源线索**仍在：
`TclsQmFix.dat` 784B、`config_mp.cfg` 7846B（= 784×10+6），二者长度关系依旧成立，值得回来做同源判定。

---

## 6. 复现（只读）

```powershell
# 解单个 .ff，导出层一
python -X utf8 CODOLServer\_mainline\ff_iw4_decrypt.py "COD OL\main\mp_playlists.ff" _cleanout\ff_layer1 --dump

# 批量
Get-ChildItem "COD OL\main\*.ff" | ForEach-Object {
  python -X utf8 CODOLServer\_mainline\ff_iw4_decrypt.py $_.FullName _cleanout\ff_layer1 --dump
}
```

依赖：`pycryptodome`（`pip install pycryptodome`）。RSA 用纯 `pow()`，无需其它库。
私钥 DER 存于 `CODOLServer\_mainline\zonekey_der.hex`（亦会回退到 IW4X 源码提取）。

---

## 7. 与既有结论的关系

| 旧说法 | 本轮更正 |
|---|---|
| `.ff` 读取/解密在 `.tvm0`/`.tls`，需运行期取证 | **层一不需要**：私钥硬编码在 IW4X 源码，可离线解 |
| `.ff` 与 `IWffu100`/`IWff0100` 同族（引擎文件系统层） | 对，且新增第三种 `IWffs100`（COD OL 自有加密容器） |
| `config_mp.cfg` 加密算法未解 | 不变；但 `.ff` 链路已打通到层一，可作为 cfg 的同源突破口 |

---

## 8. 下一步（按性价比）

1. **读 `Base.dll` 的 `IWffs100` 解码器**：由字符串池 VA（`0xDB5EC8` 附近）与
   `base+0x45BC2F`/`0x45C2BF` 附近的引用入手；`Base.dll` 的 `.tls`/`.tvm0` 是本轮未读区。
2. **同源判定**：拿 `TclsQmFix.dat`/`config_mp.cfg` 与 `.ff` 层一产物做密钥流/结构比对。
3. **IV 语义**：10 个 IV 已列全，尝试判定其是否 = 文件时间 / zone 名哈希 / 序号，
   这通常是定位引擎自定义模式的最短路径。

---

## 9. 边界

全程只读磁盘文件 + 纯离线密码学；未启动游戏、未读/写任何运行进程内存、
未改网络/路由/DNS/防火墙、未触碰 ACE/TenProtect。

---

## 10. 补充证据（同轮追加）

### 10.1 RSA 私钥就在游戏本体里（不依赖 IW4X）

`codoMP_client_shipRetail.exe` 自带同一把 RSA 私钥，逐字节相同：

```
文件偏移 0x6984B0  (VA 0xDAC4B0)，1191 字节 PKCS#1 RSAPrivateKey DER
  == IW4X FastFiles::ZoneKey  ->  True
  sha256 = 3a2f7891ac98f1fdf6a9a221c5586725157df270d6831e0ff82c383cd262cbb5
  32 位立即数引用：文件偏移 0x5BFF0、0x19C2E3
紧随其后（0x6984B0+0x4A7）是另一段 DER：30 82 01 0A 02 82 01 01 00 A5 00 6F A8 …
  -> 很可能是配套的 RSA 公钥（用于解密结果校验）
```

⇒ 解密材料完全由游戏自身携带，**纯离线可复现**。

### 10.2 `Base.dll` 自带标准 AES

`codoMP_client_shipRetailBase.dll` 内定位到标准 AES 常量集：

```
0x9CB670  256B AES 正向 S-box   (63 7C 77 7B F2 6B 6F C5 … BB 16)
0x9CB770  Te0 变换表            (C6 63 63 A5 F8 7C 7C 84 …)
0x255FB4  Te0 的另一处拷贝
0xF5F40A  Rcon 序列             (01 02 04 08 10 20 40 80 1B 36 …)
```

⇒ 层二的候选实现是 **`Base.dll` 内的软件 AES**（另一把 key 或另一种模式）。
`Base.dll` 的 `.text`（熵 7.30，含标准序言）可反汇编；`.tls`（可执行，15.5 MB）
与 `.tvm0`（32 MB）仍未解析。这是层二最短的静态入口。

### 10.3 层二已否证清单（追加）

| 假设 | 结果 |
|---|---|
| 整段 LZMA（FORMAT_RAW，dict 2^16/2^24） | **否证** |
| Base.dll 的 zlib/`uncompress` 直接解 | 否证（无 zlib 头） |
| 第二次 AES-CTR（同 key，同/异 IV） | 否证（破坏魔数或仍高熵） |

---

## 11. 第二次推进（2026-09-30 续）：覆盖到全部内容包 + 层二系统否证

### 11.1 `.ifs` 容器内嵌 fastfile 同样可解（面扩大到 23.8 GB）

`COD OL\IIPS\IIPSDownload\*.ifs` 共 **974 个、23.8 GB**，其中 **695 个内嵌
`IWff0100` fastfile**（其余为同名分片/增量）。内嵌 fastfile 与 `main\*.ff`
**结构完全一致**，同一把 AES 主密钥即可解出层一：

```
ff_dlc17_common_V18.ifs  24,060,283 B
  IWff0100 @ 0x151, version 461
  AES key = da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5
  IV      = 13547b73c37fcd01b543806587030000
  layer1  = 'IWffs100' 00 00 00 00 …
```

工具已支持直接喂 `.ifs`：`python … ff_iw4_decrypt.py <file.ifs>`。

### 11.2 主密钥与 IV 的实测结构

* **AES 主密钥全库唯一**：`da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5`
  （`.ff` 与 `.ifs` 内嵌 fastfile 全部相同）。
* **16 字节 "IV" 每文件不同且明显结构化**，例如：

```
mp_playlists.ff        ff6c10c6 db65 0000 149c1f01 0300 0000
code_post_gfx_mp.ff    cfaa3864 1209 0601 efc91b5a 8503 0000
ui_mp.ff               00a2689e 1141 8e02 b22bd822 d903 0000
```

末两字节恒为 `00 00`，且含小整数（03 / 0x85 / 0x0b …）⇒ 该 16 字节
大概率是"nonce + 版本/长度"的混合，而非纯随机 IV。这是定位层二的**关键线索**。

### 11.3 层二——本轮新增的系统性否证（全部只读实测）

| 假设 | 检验范围 | 结果 |
|---|---|---|
| CTR 计数器递增字节区间不同（非整块小端） | 穷举 16 字节内**全部**连续子区间 × 两种端序（136 组） | 只有整块小端出魔数，余者熵 7.98 |
| 流被按位偏移后是 zlib | 起始 0..63 偏移 × 0..7 位偏移 | 零命中 |
| AES-CBC / CFB(1,16) / OFB / ECB | 5 keys × 5 IV × 5 模式 | 零命中 |
| 嵌套容器（内层 IV+密文） | 内层 IV 取 8/12/16/20/24/32/36 | 零命中 |
| 滚动变换链（IW4X `ReadXFileStub` 的 rot/xor 链） | 正/逆两向 | 否证 |
| 整段 LZMA / bz2（多字典） | 偏移 0..63 | 零命中 |
| 每 8192 字节重置 IV 的 CTR | 实试 | 头后仍高熵 |

> 残差：层二既非"从 0 偏移的压缩"，也非上述任何密钥流/分组模式。
> 它极可能是**引擎自定义的位流/块编码**，实现位于 `Base.dll` 的
> 未解析区（`.tls` 15.5 MB / `.tvm0` 32 MB），或需要**运行期快照**。

### 11.4 已确认可直接产出的旁路明文

| 文件 | 状态 |
|---|---|
| `GameBabyConfig.dat` | **本就是明文**（GBK XML，腾讯安全组件配置） |
| `BugTrace.ini` | 本就是明文 |
| `tenslx.dat` | 标准 OLE2/CFB，可解出 `TS0001.dat` 流（腾讯安全组件签名数据，价值低） |
| `Game.dat` | 4 字节头 + zlib → 2878 B（位域签名数据，非资产） |
| `Tenparty.dat` | `MOSANG00` 容器 + 4 条 72B 记录（TEA 常数 δ 在场，疑似加密记录） |

---

## 12. 第二次推进：`IWffs100` 容器的精确头部布局

对 10 个 `main\*.ff` 统计层一产物，得到**恒定**的头部结构
（这是定位层二最有价值的几何约束）：

```
偏移        长度    性质
0x000       8       ASCII 魔数 'IWffs100'      （明文，恒定）
0x008       4       = 0                          （明文，恒定）
0x00C       0x120   **高熵块 288 字节**          （每文件互异，熵 7.25–7.35）
0x12C       0x30    zone 名，NUL 填充           （明文，恒定位置；如 'mp_playlists'）
0x15C 起            主体（高熵）
```

两个硬事实：

1. **zone 名恒在 +0x12C**（10/10 一致），⇒ 0x00C..0x12C 是**定长**结构，
   不是"从 0 偏移开始的连续压缩流"（否则名字位置会随数据浮动）。
2. 0x00C..0x12C 的 288 字节**每文件互异且高熵**，⇒ 它是一段**逐文件加密/编码的头扩展**。

⇒ 层二的正确提法应是：**「12 字节明文头 + 288 字节加密头扩展 + 明文名 + 主体」**，
而不是"整段 zlib"。这解释了为什么所有"整段解压"都失败。

### 12.1 下一步（据此收敛）

1. 以 **VA 0xDB5EC8（exe 内 'IWffs100' 串）** 与 **exe 0x5BFF0（指向 RSA 私钥的引用）**
   为中心，在 exe 里定位这 12+288+… 的读取序列（exe `.tp3` 静态为密文，需先解包，
   或改用运行期采样）。
2. 用 `--write-spec`/`--dump-ranges` 对客户端**已加载的 ui_mp.ff 解码头**做运行期快照：
   定位 0x00C..0x12C 那段在被引擎消费前后的形态。
3. `Base.dll` 的 AES（表 @0x9CB670 / Te0 @0x9CB770 / Rcon @0xF5F40A）若被某处调用，
   即为 288 字节块的解码器落点；Base.dll `.text` 可反汇编，`.tls`/`.tvm0` 未解析。
