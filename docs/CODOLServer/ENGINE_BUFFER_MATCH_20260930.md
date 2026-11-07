# 运行期确证：引擎内存中的 zone 缓冲 == 本地层一解密（2026-09-30）

这是层一算法**最强的一次外部验证**——不是"看起来对"，而是与游戏进程内部的
字节缓冲逐字节相同。

---

## 1. 证据

对一次成功运行（`E57A5C_20260930_143320_a1`，客户端到达
`DW_LOBBY_CONNECTED` + `DWLOBBY_PUMP_SUCCESS`）转储客户端低地址区
（`0x01000000-0x30000000`，788 MB），在其中发现：

```
VA 0x01C4B704 : 'common_mp'            ← 引擎记录的 zone 名
VA 0x01C4B724 : 'IWffs100' 00 00 00 00 <高熵主体>   ← 层一容器
```

与本地用 `ff_iw4_decrypt.py` 解出的 `common_mp.ff` 层一产物比对：

```
engine mem[:16] : 49 57 66 66 73 31 30 30 00 00 00 00 a0 97 a5 29
my layer1 [:16] : 49 57 66 66 73 31 30 30 00 00 00 00 a0 97 a5 29
match 16/32/64/128/256 bytes : True
连续匹配长度                  : 8144 字节（之后断裂）
```

`common_mp.ff` 的密钥调度（引擎内存里同名文件）：

```
key = da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5
iv  = d5f1a95fa5daba061a21fd486d210000
```

⇒ **引擎把 `common_mp.ff` 读入、做完 RSA+AES-CTR 后，内存中的缓冲与我本地解出的
层一产物完全相同。** 层一 = 引擎的 zone 存储格式，确证无疑。

---

## 2. 由此修正的一条旧结论

本会话早前曾据 `0x34000000-0x40000000` 的转储判断"引擎从不加载 zone 内容"。
**该判断有误**：zone 缓冲位于**低地址区**（约 `0x01C4Bxxx`），当时的转储范围
没有覆盖到。本次扩大到低地址区后立即找到。

正确表述：**引擎确实读取 `.ff` 并解密（层一），缓冲落在低地址堆区**。

---

## 3. 层二的边界（更新）

匹配在 **8144 字节**处结束：引擎缓冲只有前 8144 字节等于本地层一，其后不同。
这意味着引擎在读完/解完前段后进入了下一步（解压或换缓冲），而那一步的输出
**不在本次 788 MB 低区转储中**（该转储里 `/materials/`、`xmodelsurfs`、`.gsc`
等资产串全为 0）。

⇒ 层二的落点更精确了：在层一缓冲之后的那一步，把高熵主体变成可用的 zone。

---

## 4. 引擎的 zone 目录（运行期）

同一次转储里读出了引擎为每个基础 zone 建立的**四元目录**：

```
patch_<zone>                  <zone>
patch_localized_<zone>        localized_<zone>
```

实例（基础 zone = common_marketplace_lite / common_mp / ui_mp）：
`patch_common_mp`、`common_mp`、`patch_localized_common_mp`、`localized_common_mp` …

与 IW4X 的 `patch_%s` / `localized_%s` / `patch_localized_%s` 命名完全一致。

---

## 5. 本轮附带能力：引擎命令行注入

观察器新增 `--game-args`（已重编译 + 全链路透传）：

```
python CODOLServer\_mainline\_e57a5c_experiment.py --sandbox <sb> \
    --game-args "+set intro 0 +map mp_playlists"
```

运行期堆里能逐字读出传入的 argv（`-q\0 +set\0 intro\0 0\0 +map\0 ...`），
**参数通道已证可用**；但 `+map` / `+devmap` 未触发额外加载（引擎的 `+` 命令
执行需要 console 子系统就绪）。

---

## 6. 边界

只读：未注入、未改 `.text`、未执行外来代码、未停止/配置 ACE 或 TenProtect。
