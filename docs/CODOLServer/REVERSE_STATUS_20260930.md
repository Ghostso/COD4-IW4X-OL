# COD OL 逆向进度总览（截至 2026-09-30）

两条主线，当前**汇合于同一个瓶颈**。

---

## A. fastfile（`.ff`）加密链

### A1. 层一 —— 已攻克并三重确证

| 项 | 结论 | 级别 |
|---|---|---|
| 容器格式 | `IWff0100` 头(21B) + RSA-2048 块(256B) + AES-CTR 主体 | 已证 |
| RSA 私钥 | 与 IW4X `ZoneKey` 逐字节相同；**游戏自己 exe 也内置同一把**（0x6984B0，1191B DER，sha256 `3a2f7891…`） | 已证 |
| 密钥块 | PKCS#1 v1.5 → 40B payload = AES-192 key[24] + IV[16] | 已证 |
| 主密钥 | 全库唯一 `da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5` | 已证 |
| 计数器 | libtomcrypt CTR：整块小端自增，初值=IV | 已证 |
| 加密栈 | 客户端**静态链接 OpenSSL 1.1.1**（239 个 `crypto\*.c` 源文件，含 `rsa_pk1.c`/`e_aes.c`/`bn_exp.c`） | 已证 |

**"三重确证"**：① 纯 Python `pow()` 手写 RSA + pycryptodome AES-CTR **字节级复现**；
② 10/10 个 `main\*.ff` 全部解出 `IWffs100`；③ 客户端自带 OpenSSL，算法是标准构造。

**覆盖面**：`main\*.ff`（10 个）+ `IIPS\IIPSDownload\*.ifs` 内嵌 fastfile
（**974 个内容包 / 23.8 GB，其中 695 个内嵌 IWff**），同一把主密钥全部可解层一。

工具：`CODOLServer\_mainline\ff_iw4_decrypt.py`（支持 `.ff` 与 `.ifs`）。

### A2. 层二 —— 未解（边界已收敛）

层一产物结构（10 文件恒定）：

```
0x000  8    'IWffs100'           明文
0x008  4    version(=0)          明文
0x00C  0x120 高熵块 288B          每文件互异
0x12C  0x30  zone 名 NUL 填充     明文（如 'mp_playlists'）
0x15C 起     主体（高熵）
```

主体零字节仅占 **0.5%** ⇒ 确为压缩/加密态。

**已机械否证**：zlib / raw-deflate / gzip / lzma / bz2 / **LZ4** /
AES ECB·CBC·CFB·OFB / CTR 计数器全字节子区间×端序（136 组）/
逐位偏移 / 嵌套容器 / 滚动变换链 / 每 8192B 重置 IV。

**解码器落点**：exe 的 fastfile 读取区（VA 0x45Cxxx）在运行期镜像里是
**数据指针表 + 混淆区**（对三个魔数各仅 1 处 dword 引用、无标准序言），
静态不可直读；`Base.dll` 自带标准 AES 表（0x9CB670 / 0x9CB770 / Rcon 0xF5F40A）
但未定位到调用点。

---

## B. 大厅协议 ⑤（复活主线）

承接 `SESSION_20260930_STATUS.md`：

* ①–④ 稳定可复现；
* ⑤ 根因 = **服务端未应答 `0x85` 校验帧**；
* `0x85` 校验值算法已定性为 **SHA-1**（`0xC77920/60/30` 三件套 + `xor 0x5C` 预变换），
  但**"喂进去的字节序列 / 比对方向"未闭合**；
* 回声方案实测否证；provider id = 2 已定位。

---

## C. 两线汇合点

```
层二解码 需要引擎真正加载一个 zone（loadzone / 进地图）
复活 ⑤   需要打通大厅协议才能进地图
                          |
                          v
       两者卡在同一个"进入地图"触发点上
```

**运行期实测（已更正）**：早前据 `0x34..0x40` 段的转储判断"从不加载 zone"，
**该判断有误**——zone 缓冲在**低地址区**（约 `0x01C4Bxxx`）。扩大到
`0x01..0x30` 后立即找到引擎的层一缓冲，并与本地解密**逐字节相同**（见
`ENGINE_BUFFER_MATCH_20260930.md`）。

⇒ 引擎**确实读取并解密 `.ff`（层一）**，缓冲落在低地址堆；
层二就是紧随其后的那一步（匹配在 8144 字节处断裂）。

---

## D. 已产出的明文资料

| 文件 | 内容 |
|---|---|
| `ASSET_TYPE_TABLE.txt` | 完整 IW4 XAssetType 表（42 类） |
| `ENGINE_FF_REGISTRY.csv` | 引擎登记的 468 个 zone（运行期抓取） |
| `IFS_CONTENT_MANIFEST.csv` | 974 个磁盘内容包（zone/版本/大小/路径） |
| `CLIENT_OPENSSL_SOURCES.txt` | 客户端 OpenSSL 1.1.1 的 239 个 crypto 源文件 |
| `CLIENT_OPENSSL_NOTES.md` | 加密栈证据说明 |
| `_cleanout\ff_layer1\*.layer1.bin` | 10 个 `main\*.ff` 的层一产物（38.5 MB） |
| `_mainline\ff_zonekeys.json` | 每文件 AES key / IV |
| `_mainline\zonekey_der.hex` | 1191B RSA 私钥 DER |

---

## E. 动态链路新增：引擎命令行注入（本轮）

给观察器加了 `--game-args`，可在 `"<exe>" -q` 后追加任意参数；
已逐层透传（`capture_elevated_network.ps1` → `elevated_ifs1_observer.ps1` → `AboProbe`）
并接入实验驱动器：

```
python CODOLServer\_mainline\_e57a5c_experiment.py --sandbox <sb> --attempts 3 \
    --game-args "+set intro 0 +map mp_playlists"
```

**已证**：引擎接收并保存了完整 argv。运行期堆（VA 0x3999B000）里可读出

```
...\codoMP_client_shipRetail.exe\0 -q\0 +set\0 intro\0 0\0 +map\0 mp_playlists\0
```

⇒ `+<cmd>` 参数通道**确实到达引擎**（exe 本身含 `+set intro 0` 字面量与 `+set` 解析器）。

**但**：`+map mp_playlists` 未触发 zone 加载（128 MB 转储里仍无层一产物 / RSA 块 / 资产串）。
说明 `map` 属服务端命令，或在纯客户端下需要更完整的初始化；zone 加载仍未触发。

（观察器已重编译；旧版备份于 `AboProbe.exe.bak_before_gargs`。）

---

## F. 下一步（按性价比）

1. **触发一次 zone 加载**（解层二的唯一入口）：
   - 验证引擎 console（`devmap` / `map` / `map_restart` 字符串在场，release 版是否可用未知）；
   - 或在观察器里用 `--write-spec` 构造 zone 已加载状态（需先定位 zone 管理对象）。
2. **用 `--game-args` 继续找能加载 zone 的入口**：`+devmap`、`+set` 系列
   （如强制 game state / 前端加载），或 `+exec players/config_mp.cfg`。
3. **解包 exe 的 `.tp3`** → 读层二解码器（工作量最大，但一次解决）。
4. **闭合 ⑤ 的 `0x85` SHA-1 应答** → 前进到地图 → zone 加载（一箭双雕）。

---

## G. 边界

全程只读：未注入、未改 `.text`、未执行外来代码、未停止/配置 ACE 或 TenProtect。
运行期操作为"启动 + 只读观测 + 既有 host/port 数据写入"。
